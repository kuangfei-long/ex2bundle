from .Model import Model
from abc import abstractmethod
import pandas as pd
import numpy as np
import json
from os.path import join
import logging


class SuDocuBase(Model):

    def __init__(self, data_path, shared_docs_path, nTopics, time_limit=100):
        super().__init__(data_path, shared_docs_path, nTopics)
        self.data_path = data_path
        self.shared_docs_path = shared_docs_path
        self.nTopics = nTopics
        self.df = pd.read_csv(self.data_path, dtype= {"pid":"int64", "name":"object","sid":"int64", "sentence":"object",
                          "score":"float64", "topic_0":"float64", "topic_1":"float64",
                          "topic_2":"float64", "topic_3":"float64", "topic_4":"float64",
                          "topic_5":"float64", "topic_6":"float64", "topic_7":"float64",
                          "topic_8":"float64", "topic_9":"float64"}, sep=";")

        # with open(join(self.shared_docs_path, "state_indices.txt")) as f:
        #     file = f.read()
        #     f.close()
        # self.state_indices = json.loads(file)

        self.time_limit = time_limit

        # create an array of the topic names
        self.topic_names = np.array(['topic_' + str(i) for i in range(self.nTopics)])
    

    ###
    #    Helper function to return the topic score and length constraints
    #        used by SuDocu
    ### 
    def get_bounds(self, example_summaires):        
        # instantiate a numpy array to hold the topic scores
        #     for every sentence in every summary
        topic_sums = np.zeros((len(example_summaires), self.nTopics))
        
        avg_sum_len = 0.0

        # iterate over every example summary
        for i in range(len(example_summaires)):
            # get the example currently being processed
            ex = example_summaires[i]
            
            # get all the sentence id's for this summary
            sid = int(ex["state_id"])
            sentence_ids = [int(s) for s in ex["sentence_ids"]]

            # keep track of the lengths of the example summaries
            avg_sum_len += float(len(sentence_ids))

            # iterate over every topic
            for topic_id in range(self.nTopics):
                topic_sums[i, topic_id] = np.sum(
                    np.array(
                        [
                            np.array(self.df[self.df["sid"] == sid]["topic_" + str(topic_id)])[0]
                            for sid in sentence_ids
                        ]
                    )
                )

        # get the min and max of every topic from across all the summariess
        topic_min = list(np.min(topic_sums, axis=0))
        topic_max = list(np.max(topic_sums, axis=0))
        avg_sum_len = avg_sum_len / len(example_summaires)

        # instantiate a numpy array to hold the generated topic bounds
        topic_query_bounds = np.zeros((self.nTopics, 2))
        
        # I am not entirely sure why this and the rounding is here
        #     but this is the Vanillia SuDocu code
        eps = 1e-4
        
        for i in range(len(topic_min)):
            topic_query_bounds[i, 0] = round(topic_min[i] * 0.9 - eps, 4)
            topic_query_bounds[i, 1] = round(topic_max[i] * 1.1 + eps, 4)
                        
        # check that the mean and stddev array are 1-D
        assert topic_query_bounds.shape[0] == self.nTopics, "query bounds are not nTopics Long: SuDocuBase -> get_bounds"
        
        # check that the mean and stddev array are of proper length
        assert topic_query_bounds.shape[1] == 2, "topic_query_bounds not 2-D in second dimension: SuDocuBase -> get_bounds"
            
        return (topic_query_bounds, avg_sum_len)    # end of get_bounds() method

    


    # intentionally not overwriting the most important behavior here, this is left up to the children classes to implement
    @abstractmethod
    def get_predicted_summary(self, target_doc, example_summaires, processed_ctr):
        pass
