
import numpy as np
import docplex.mp.model as cpx
from ..utils.filtering import Sentence_Prefilter_Wrapper
from ..utils.objective_functions import Objective_Function_Wrapper
from .SuDocuBase import SuDocuBase


class SuDocu_NNBS_BS_RTL(SuDocuBase):

    def __init__(self, data_path, shared_docs_path, nTopics, max_solvs=50, length_modifier=0.25):
        super().__init__(data_path, shared_docs_path, nTopics)

        
        self.max_solvs = max_solvs                   # number of times to run the "relaxed" solution
        self.length_modifier = length_modifier       # +/- avg length constraint value
        self.filter_obj = Sentence_Prefilter_Wrapper(data_path, shared_docs_path, nTopics)
        self.obj_func_obj = Objective_Function_Wrapper(data_path, shared_docs_path, nTopics)

    # override abstract method
    def get_predicted_summary(self, target_doc, example_summaires, processed_ctr, bounds=None):

        # generate all of the necessary SuDocu info
        if (bounds == None):
            bounds, avg_len = self.get_bounds(example_summaires)
        else:
            _, avg_len = self.get_bounds(example_summaires)
        
        ex_embedding = self.obj_func_obj.get_ex_embedding(example_summaires)
        example_sentences = self.obj_func_obj.get_ex_sentences(example_summaires)
        avg_len_step = self.length_modifier * avg_len
        
        assert len(bounds) == self.nTopics, "SuDocu_NNBS_BS_RTL->get_predicted_summary: topic bounds incorrect shape"

        # variable to track the status of the ILP problem
        status = "none"

        # variable to hold the current size multiplier
        size_mult = 2

        # variable to track the number of times this ILP has been formed/solved
        solv_ctr = 0

        # variable to track if we need to create a default summary or not
        create_default_summary = False

        # loop until an optimal soltuion is reached
        #     or until we have evaluated the ILP 
        while status != 'Optimal' and solv_ctr < self.max_solvs:
            
            # if this statment is true we are in a resolve situation
            if (solv_ctr > 0):
                print("Resolving with top_k = %d" % size_mult)
            
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

            # create a DocPLEX (CPLEX) problem instance
            opt_model = cpx.Model(name="SuDocu_PaQL")

            # Integer variables
            package_vars = opt_model.integer_var_dict(sentence_ids, lb=0, ub=1, name="s")

            # Constraints
            for j, topic in enumerate(topic_scores):
                opt_model.add_constraint(ct=opt_model.sum(topic[i] * package_vars[sid] for i, sid in enumerate(sentence_ids)) >= bounds[j][0], ctname="constraint_min_topic{0}".format(j))
                opt_model.add_constraint(ct=opt_model.sum(topic[i] * package_vars[sid] for i, sid in enumerate(sentence_ids)) <= bounds[j][1], ctname="constraint_max_topic{0}".format(j))
            
            # add summary length constraints
            opt_model.add_constraint(ct=opt_model.sum(package_vars) >= avg_len-avg_len_step, ctname="constraint_min_len")
            opt_model.add_constraint(ct=opt_model.sum(package_vars) <= avg_len+avg_len_step, ctname="constraint_max_len")
            
            # Create Objective function
            objective = opt_model.sum(combined_score[i] * package_vars[sid] for i, sid in enumerate(sentence_ids))
    
            # Add objective to model
            opt_model.maximize(objective)
            
            # Solve the ILP
            solu = opt_model.solve()
            solv_ctr += 1
            size_mult += 1
            if solu is None:
                status = "none"
            else:
                status = "Optimal"

        selected_sentence_ids = []
        
        # build summary
        summary = []
        summary_indicies = []
        
        if (status != "Optimal"):
            # extract the approperiate filtered sentences
            selected_sentence_ids = self.filter_obj.nearest_neighbor_bert_summary_filtering(example_summaries=example_summaires,  test_doc=target_doc, top_k=int(avg_len))
            create_default_summary = True
            summary.append("def_sum")
            print("Creating default summary")
        
        else:
            # iterate over the results for the optimal summary
            for var, val in solu.iter_var_values():
                if val > 0:
                    selected_sentence_ids.append(var.name)
                
        
        # iterate over every sentence id in the optimal summary
        for sid in selected_sentence_ids:
            if (create_default_summary):
                index = int(sid)
            else:
                index = int(sid[2:])
            summary_indicies.append(index)
            sentence = sub_df[sub_df['sid'] == index]['sentence'].to_numpy()[0]
            summary.append(str(sentence))
        
        return (" ".join(summary), summary_indicies)    # end get_predicted_summary() method

