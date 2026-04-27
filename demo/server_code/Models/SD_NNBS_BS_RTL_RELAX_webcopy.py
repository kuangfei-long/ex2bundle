
import numpy as np
import docplex.mp.model as cpx
import docplex.cp.parameters as params
from docplex.mp.relaxer import Relaxer
from docplex.mp.conflict_refiner import ConflictRefiner
from docplex.mp.priority import Priority
from utils.filtering import Sentence_Prefilter_Wrapper
from ..utils.objective_functions import Objective_Function_Wrapper
from .SuDocuBase import SuDocuBase


# NOTES!
#   try cplex returned problem constraints
#   think about stats for topic scores
#   "random package" based stepping

class SuDocu_NNBS_BS_RTL_Relax(SuDocuBase):

    def __init__(self, data_path, shared_docs_path, nTopics, max_solvs=50, length_modifier=0.25):
        super().__init__(data_path, shared_docs_path, nTopics)

        myparams = params.CpoParameters(LogVerbosity='Quiet', Presolve='On')
        myparams.set_attribute('Presolve', 'On')

        
        self.max_solvs = max_solvs                   # number of times to run the "relaxed" solution
        self.length_modifier = length_modifier       # +/- avg length constraint value
        self.filter_obj = Sentence_Prefilter_Wrapper(data_path, shared_docs_path, nTopics)
        self.obj_func_obj = Objective_Function_Wrapper(data_path, shared_docs_path, nTopics)

        self.utilized_bounds = None
        self.slider_values = None

    # override abstract method
    def get_predicted_summary(self, target_doc, example_summaires, processed_ctr, bounds=None, first_gen=False, slider_alg_vals=None, alg_one_version=1, alg_two_version=1):

        if first_gen:
            print("Using Relaxation Algorithm #1")
        elif first_gen == False and slider_alg_vals != None:
            print("Using Relaxation Algorihtm #2")
        else:
            print("ERROR -- Improperly formatted summary request. Needs to be either first_gen, or not first_gen and have slider alg. values passed in. Exiting")
            return ("", [])

        # generate all of the necessary SuDocu info
        if (bounds == None):
            bounds, avg_len = self.get_bounds(example_summaires)
        else:
            _, avg_len = self.get_bounds(example_summaires)
        
        ex_embedding = self.obj_func_obj.get_ex_embedding(example_summaires)
        example_sentences = self.obj_func_obj.get_ex_sentences(example_summaires)
        avg_len_step = self.length_modifier * avg_len

        target_df = self.df[(self.df['name'] == target_doc)]
        
        assert len(bounds) == self.nTopics, "SuDocu_NNBS_BS_RTL->get_predicted_summary: topic bounds incorrect shape"
        
        bounds = np.array(bounds)

        ####
        # create the relaxation variables
        ####
        
        # 1.    find the target_doc topic scores
        target_doc_scores = target_df[self.topic_names].to_numpy().sum(axis=0)
        # print("\ttarget_doc_scores: ")
        # print(target_doc_scores)

        # 2.    divide the topic scores by the number of sentences in the doc
        target_doc_topic_step_sizes = target_doc_scores / (target_df.shape[0] / 2.0)
        # print("\ttarget_doc_topic_step_sizes: ")
        # print(target_doc_topic_step_sizes)

        # variables for second relax algorithm
        slider_diffs = None
        relax_topics = None
        slider_vals = None

        # get the set of modified topics
        if (slider_alg_vals != None):
            slider_diffs = slider_alg_vals["slider_val_diffs"]
            relax_topics = np.nonzero(slider_diffs)
            slider_vals = slider_alg_vals["slider_vals"]
        else:
            relax_topics = np.zeros((self.nTopics))


        ####
        # Set up target document data / ILP metrics
        ####
        
        # variable to hold the current size multiplier
        size_mult = 2.25
        
        # extract the approperiate filtered sentences
        filtered_sentence_ids = self.filter_obj.nearest_neighbor_bert_summary_filtering(example_summaries=example_summaires, test_doc=target_doc, top_k=int(avg_len * size_mult))

        # create a DataFrame containing only the data relavent to 
        #     the state about to be summized, and that are contained in
        #     the list of nearest neighbor sentences
        sub_df = self.df[(self.df['name'] == target_doc) & (self.df['sid'].isin(filtered_sentence_ids))]

        # get all the sentence id's for this state
        sentence_ids = sub_df["sid"].to_numpy()

        # get all the topic score distributions for all the 
        #     the sentences in this state
        topic_scores = sub_df[self.topic_names].to_numpy().transpose()

        # get the actual sentences from the target "document", 
        #     in this case all the prefiltered sentences
        sentences_target = sub_df['sentence'].to_numpy()
        
        # calculate the SBERT-Sum merit score
        bs_merit_scores = self.obj_func_obj.calculateBSMeritScore(sentence_ids, target_doc, ex_embedding)
        
        # get the cleaned sentences from the target document
        sentences_target_clean = self.obj_func_obj.cleanSentences(sentences_target)

        # get the cleaned example_summary sentences
        example_sentences_clean = self.obj_func_obj.cleanSentences(example_sentences)
                    
        # calculate the TFIDF scores of the target sentences
        #     based on the TF of the example summaries
        tfidf_scores = self.obj_func_obj.calculateNormalizedTFIDF(sentences_target_clean, example_sentences_clean)

        # calculate the LPR scores of the target sentences
        lpr_scores = self.obj_func_obj.calculateNormalizedLPR(sentences_target_clean, example_sentences_clean)

        # array to hold the total merit score used by the objective function
        combined_score = []

        # add the tfidf score to each sentences merit score
        for bs_ms, tf_idf, lpr in zip(bs_merit_scores, tfidf_scores, lpr_scores):
            combined_score.append(bs_ms+tf_idf+lpr)

        # array to hold the combined objective function scores
        combined_score = np.array(combined_score)

        # save off info if approperiate
        if processed_ctr % 10 == 0:
            print("Number of candidate sentences: %d" % (sentence_ids.shape[0]))


        #####
        # Setup variables to track the relaxation algorithm status
        ####

        # variable to track the status of the ILP problem
        status = "none"

        # variable to track the number of times this ILP has been formed/solved
        solv_ctr = 0
        
        
        # loop until an optimal soltuion is reached
        #     or until we have evaluated the ILP 
        while status != 'Optimal':
            
            # if this statment is true we are in a resolve situation
            # if (solv_ctr > 0 and solv_ctr % 25 == 0):
            #     print("Resolving with solv_ctr = %d" % solv_ctr)

            # calculate a step multiplier
            step_mult = int(float(solv_ctr) / 10.0)

            if step_mult < 1:
                step_mult = 1


            # create a DocPLEX (CPLEX) problem instance
            opt_model = cpx.Model(name="SuDocu_PaQL")

            # Integer variables
            package_vars = opt_model.integer_var_dict(sentence_ids, lb=0, ub=1, name="s")

            # Algorithm One constraints
            if (first_gen == True):
                if (alg_one_version == 2):
                    for j, topic in enumerate(topic_scores):
                        # Constraints
                        for i, sid in enumerate(sentence_ids):
                            opt_model.add_constraint(ct=opt_model.sum(topic[i] * package_vars[sid]) >= bounds[j][0], ctname="constraint_min_topic{0}".format(j))
                            opt_model.add_constraint(ct=opt_model.sum(topic[i] * package_vars[sid]) <= bounds[j][1], ctname="constraint_max_topic{0}".format(j))
                elif (alg_one_version == 1):
                    self.cplex_infeasible_alg_one(opt_model, package_vars, bounds, topic_scores, sentence_ids, target_doc_topic_step_sizes, relax_topics, solv_ctr, step_mult)
                else:
                    #(self, model, package_vars, bounds, topic_scores, sentence_ids, target_doc_topic_step_sizes, solv_ctr):
                    self.smallest_range_alg_one(opt_model, package_vars, bounds, topic_scores, sentence_ids, target_doc_topic_step_sizes, solv_ctr)
               

            # Algorithm Two Constraints
            elif (first_gen == False and slider_alg_vals != None):
                # print("stable vs current bounds difference: %.4f" % np.sum(np.subtract(bounds, slider_alg_vals['stable_bounds'])))

                if (alg_two_version == 2):
                    for j, topic in enumerate(topic_scores):
                        # Constraints
                        for i, sid in enumerate(sentence_ids):
                            opt_model.add_constraint(ct=opt_model.sum(topic[i] * package_vars[sid]) >= bounds[j][0], ctname="constraint_min_topic{0}".format(j))
                            opt_model.add_constraint(ct=opt_model.sum(topic[i] * package_vars[sid]) <= bounds[j][1], ctname="constraint_max_topic{0}".format(j))
                elif (alg_two_version == 1):
                    # (self,model, package_vars, bounds, topic_scores, sentence_ids, slider_vals, slider_diffs, slider_alg_vals, relax_topics, solv_ctr):
                    self.cplex_infeasible_alg_two(opt_model, package_vars, bounds, topic_scores, sentence_ids, slider_vals, slider_diffs, slider_alg_vals, relax_topics, solv_ctr, step_mult)
                else:
                    # (self, opt_model, package_vars, bounds, topic_scores, sentence_ids, slider_vals, slider_diffs, solv_ctr):
                    self.largest_x_diff_alg_two(opt_model, package_vars, bounds, topic_scores, sentence_ids, slider_vals, slider_diffs, slider_alg_vals, solv_ctr)
                
                
            elif (solv_ctr > 5000):
                # if we have solved more than 5000 problems, revert to the stable bounds and run again
                print("\n\n!!!!!!!!!!!!!!!!! Stable bounds solve !!!!!!!!!!!!!!!!!!!!!!!!\n\n")
                bounds = slider_alg_vals['stable_bounds']
                for j, topic in enumerate(topic_scores):
                    # Constraints
                    for i, sid in enumerate(sentence_ids):
                        opt_model.add_constraint(ct=opt_model.sum(topic[i] * package_vars[sid]) >= bounds[j][0], ctname="constraint_min_topic{0}".format(j))
                        opt_model.add_constraint(ct=opt_model.sum(topic[i] * package_vars[sid]) <= bounds[j][1], ctname="constraint_max_topic{0}".format(j))
        
            # add summary length constraints
            opt_model.add_constraint(ct=opt_model.sum(package_vars) >= avg_len-avg_len_step, ctname="constraint_min_len")
            opt_model.add_constraint(ct=opt_model.sum(package_vars) <= avg_len+avg_len_step, ctname="constraint_max_len")
            
            # Create Objective function
            objective = opt_model.sum(combined_score[i] * package_vars[sid] for i, sid in enumerate(sentence_ids))
    
            # Add objective to model
            opt_model.maximize(objective)
            
            # Solve the ILP
            solu = opt_model.solve(log_output=False);
            solv_ctr += 1
            if solu is None:
                status = "none"
            else:
                status = "Optimal"

            # get the problem constraints as needed
            if ((alg_one_version == 1 or alg_two_version == 1) and status == "none"):
                cr = ConflictRefiner()
                cr_res = cr.refine_conflict(opt_model, display=False)
                
                relax_topics = set()

                for conflict in cr_res.iter_conflicts():
                    if "topic" in conflict[0]:
                        relax_topics.add(int(conflict[0][-1]))

                relax_topics = list(relax_topics)

            # Relx ILP using built-in CPLEX relaxation libraries, no custom code really
            if (alg_one_version == 2 and alg_two_version == 2 and status == "none"):

                # make the overall length constraint manditory
                for ctd in opt_model.find_matching_linear_constraints("constraint_min_len"):
                    ctd.priority = Priority.VERY_HIGH
                
                for ctd in opt_model.find_matching_linear_constraints("constraint_max_len"):
                    ctd.priority = Priority.VERY_HIGH

                # make lower bounds manditory (avoid negative constraints)
                for ctd in opt_model.find_matching_linear_constraints("constraint_min"):
                    ctd.priority = Priority.VERY_HIGH

                # if first gen, then relax without priority
                if (first_gen):
                    rx = Relaxer()
                    solu = rx.relax(opt_model, log_output=False)
                
                # otherwise, with the second gen keep the user supplied settings
                #    as high/medium priority
                else:
                    # loop over constraints, adding priorities
                    for topic_id in relax_topics:
                        for ctd in opt_model.find_matching_linear_constraints("constraint_max_topic{0}".format(topic_id)):
                            ctd.priority = Priority.HIGH
                        
                        # # prevents us from going into the negatives
                        # for ctd in opt_model.find_matching_linear_constraints("constraint_min_topic{0}".format(topic_id)):
                        #     ctd.priority = Priority.MANDATORY
                    rx = Relaxer()
                    solu = rx.relax(opt_model)

                if solu is None:
                    status = "none"
                else:
                    status = "Optimal"

                # extract relaxed constraints to return and use for website purposes
                # lower-bounds
                # for topic_id in range(self.nTopics):
                #     for ctd in opt_model.find_matching_linear_constraints("constraint_min_topic{0}".format(topic_id)):
                #         bounds[topic_id][0] = bounds[topic_id][0] + rx.get_relaxation(ctd)
                
                # # upper-bounds
                # for topic_id in range(self.nTopics):
                #     for ctd in opt_model.find_matching_linear_constraints("constraint_max_topic{0}".format(topic_id)):
                #         bounds[topic_id][1] = bounds[topic_id][1] + rx.get_relaxation(ctd)

                print("Status after relaxing: %s" % status)                

        selected_sentence_ids = []

        print("Solved ILP with %d iterations" % solv_ctr)

        # see what the final difference is
        if (not first_gen):
            print("stable vs current bounds difference: %.4f" % np.sum(np.subtract(bounds, slider_alg_vals['stable_bounds'])))
        
        # set the global utilized_bounds variable
        self.utilized_bounds = bounds

        self.slider_values = slider_vals
        
        # build summary
        summary = []
        summary_indicies = []
        
        # iterate over the results for the optimal summary
        for var, val in solu.iter_var_values():
            if val > 0:
                selected_sentence_ids.append(var.name)
                
        # iterate over every sentence id in the optimal summary
        for sid in selected_sentence_ids:
            index = int(sid[2:])
            summary_indicies.append(index)
            sentence = sub_df[sub_df['sid'] == index]['sentence'].to_numpy()[0]
            summary.append(str(sentence))

        # print(" ".join(summary))
        
        print(bounds)
        print(slider_alg_vals['stable_bounds'])

        return (" ".join(summary), summary_indicies)    # end get_predicted_summary() method 


    def get_utilized_bounds(self):
        return self.utilized_bounds.tolist()

    def get_utilized_slider_values(self):

        return np.array(self.slider_values).tolist()

    def calculateBoundsFromImportanceScore(self, topic_idx, slider_val, slider_values_dict):
        center = slider_values_dict['center_slopes'][topic_idx]*slider_val + slider_values_dict['center_offsets'][topic_idx];
    
        bound_offset = slider_values_dict['bound_offsets'][topic_idx] - np.abs(slider_values_dict['bound_slopes'][topic_idx]*slider_val)

        lower_bound = (center - bound_offset)
        upper_bound = (center + bound_offset)

        if (lower_bound < 0):
            lower_bound = 0.0

        return [lower_bound, upper_bound]

    def smallest_range_alg_one(self, model, package_vars, bounds, topic_scores, sentence_ids, target_doc_topic_step_sizes, solv_ctr, step_mult=1):
         # find the topic with the smallest ranges
        smallest_range_topic_idx = np.argmin(np.abs(np.subtract(bounds[:,1], bounds[:,0])))
        # print(np.subtract(bounds[:,1], bounds[:,0]))
        # print("\tsmallest_range_idx: %d" % smallest_range_topic_idx)

        # Constraints
        for j, topic in enumerate(topic_scores):
            if (j == smallest_range_topic_idx and solv_ctr > 0):
                # print("old bounds: (%.4f, %.4f)" % (bounds[j][0], bounds[j][1]))
                # adjust the lower bound by the appropriate step-size, clipping at zero as necessary
                bounds[j][0] = bounds[j][0] - step_mult*target_doc_topic_step_sizes[j] if bounds[j][0] - step_mult*target_doc_topic_step_sizes[j] > 0 else 0.0
                # adjust the upper bound
                bounds[j][1] = bounds[j][1] + step_mult*target_doc_topic_step_sizes[j]
                # print("new bounds: (%.4f, %.4f)" % (bounds[j][0], bounds[j][1]))

            for i, sid in enumerate(sentence_ids):
                model.add_constraint(ct=model.sum(topic[i] * package_vars[sid]) >= bounds[j][0], ctname="constraint_min_topic{0}".format(j))
                model.add_constraint(ct=model.sum(topic[i] * package_vars[sid]) <= bounds[j][1], ctname="constraint_max_topic{0}".format(j))

    def largest_x_diff_alg_two(self, model, package_vars, bounds, topic_scores, sentence_ids, slider_vals, slider_diffs, slider_alg_vals, solv_ctr, step_mult=1):
        # find the modified topic with the largest x-axis difference
        print(slider_diffs)
        largest_xdiff_topic = np.argmax(np.abs(slider_diffs))
        # print("\largest_xdiff_topic: %d" % largest_xdiff_topic)

        # Constraints
        for j, topic in enumerate(topic_scores):

            if (j == largest_xdiff_topic and solv_ctr > 0):
                # print("slider_vals[j]: %.4f" % slider_vals[j])
                # print("old bounds: (%.4f, %.4f)" % (bounds[j][0], bounds[j][1]))
                slider_vals[j] = slider_vals[j] + step_mult*(np.sign(slider_diffs[j]))
                bounds[j] = self.calculateBoundsFromImportanceScore(slider_val=slider_vals[j], topic_idx=j, slider_values_dict=slider_alg_vals)
                # print("slider_vals[j]: %.4f" % slider_vals[j])
                # print("new bounds: (%.4f, %.4f)" % (bounds[j][0], bounds[j][1]))
                # print()

                # update x difference (start - end)
                slider_diffs[j] = slider_alg_vals['prev_slider_vals'][j] - slider_vals[j]

            for i, sid in enumerate(sentence_ids):
                model.add_constraint(ct=model.sum(topic[i] * package_vars[sid]) >= bounds[j][0], ctname="constraint_min_topic{0}".format(j))
                model.add_constraint(ct=model.sum(topic[i] * package_vars[sid]) <= bounds[j][1], ctname="constraint_max_topic{0}".format(j))

    def cplex_infeasible_alg_one(self, model, package_vars, bounds, topic_scores, sentence_ids, target_doc_topic_step_sizes, relax_topics, solv_ctr, step_mult=1):
        # Constraints
        for j, topic in enumerate(topic_scores):
            if (j in relax_topics and solv_ctr > 0):
                # print("old bounds %d: (%.4f, %.4f)" % (j, bounds[j][0], bounds[j][1]))
                # adjust the lower bound by the appropriate step-size, clipping at zero as necessary
                bounds[j][0] = bounds[j][0] - step_mult*target_doc_topic_step_sizes[j] if bounds[j][0] - step_mult*target_doc_topic_step_sizes[j] > 0 else 0.0
                # adjust the upper bound
                bounds[j][1] = bounds[j][1] + step_mult*target_doc_topic_step_sizes[j]
                # print("new bounds %d: (%.4f, %.4f)" % (j, bounds[j][0], bounds[j][1]))

            for i, sid in enumerate(sentence_ids):
                model.add_constraint(ct=model.sum(topic[i] * package_vars[sid]) >= bounds[j][0], ctname="constraint_min_topic{0}".format(j))
                model.add_constraint(ct=model.sum(topic[i] * package_vars[sid]) <= bounds[j][1], ctname="constraint_max_topic{0}".format(j))


    def cplex_infeasible_alg_two(self, model, package_vars, bounds, topic_scores, sentence_ids, slider_vals, slider_diffs, slider_alg_vals, relax_topics, solv_ctr, step_mult=1):

        # Constraints
        for j, topic in enumerate(topic_scores):
            if (j in np.array(relax_topics) and solv_ctr > 0):
                # print("old bounds %d: (%.4f, %.4f)" % (j, bounds[j][0], bounds[j][1]))
                slider_vals[j] = slider_vals[j] + step_mult*(np.sign(slider_diffs[j]))
                bounds[j] = self.calculateBoundsFromImportanceScore(slider_val=slider_vals[j], topic_idx=j, slider_values_dict=slider_alg_vals)
                # print("new bounds %d: (%.4f, %.4f)" % (j, bounds[j][0], bounds[j][1]))

            for i, sid in enumerate(sentence_ids):
                model.add_constraint(ct=model.sum(topic[i] * package_vars[sid]) >= bounds[j][0], ctname="constraint_min_topic{0}".format(j))
                model.add_constraint(ct=model.sum(topic[i] * package_vars[sid]) <= bounds[j][1], ctname="constraint_max_topic{0}".format(j))