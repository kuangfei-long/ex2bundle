import pandas as pd
import numpy as np
import sys
from io import StringIO
import os
from os import listdir
from os.path import isfile, join
import json
import math
import random
from itertools import combinations
import time
from timeit import default_timer as timer
from scipy.spatial.distance import cosine, jensenshannon


class Sentence_Prefilter_Wrapper:
    def __init__(self, data_path, shared_docs, nTopics):
        self.data_path = data_path
        self.shared_docs_path = shared_docs
        with open(join(self.shared_docs_path, "state_indices.txt")) as f:
            file = f.read()
            f.close()
        self.doc_indicies = json.loads(file)
        self.nTopics = nTopics
        self.df = pd.read_csv(self.data_path, sep=";")
        self.topic_names = ["topic_" + str(i) for i in range(self.nTopics)]

    ###
    #
    # Find the top-k closest (in terms of cosine distance) sentences from the target documents
    #     and the average SBERT embedding of the sentences from the example summaries
    #
    ###
    def nearest_neighbor_bert_summary_filtering(self, example_summaries, test_doc, top_k):
        filtered_sentences = []                  # array to hold the selected sentences
        test_doc_comparsion_data = None          # variables to reference the selected target document data

        # load the NPZ file storing the SBERT embeddings for this document
        file_path = join(self.shared_docs_path, "StateDocuments/", test_doc.strip() + "sudocu.npz")
        data = np.load(file_path)
        test_doc_comparsion_data = data['embedding']

        # document index offset
        test_doc_idx_offset = self.doc_indicies[test_doc][0]

        # list to hold the comparsion data from the example summaries
        ex_summary_comparsion_data = []

        # iterate over all the example summaries
        for ex_sum in example_summaries:
            # extract all the relavent info for this example summary
            sentence_ids = [int(s) for s in ex_sum["sentence_ids"]]
            doc_name = ex_sum['state_name']
            state_id = ex_sum['state_id']
            
            # if the similaity measure is SBERT cosine simuilairty
            npz_path = join(self.shared_docs_path, "StateDocuments/", doc_name.strip() + "sudocu.npz")
            data = np.load(npz_path)
            ex_state_comp_data = data['embedding']
                
            ex_doc_idx_offset = self.doc_indicies[doc_name][0]
                
            # iterate over every sentence id in this example, and extract the 
            #     approperiate SBERT sentence embeddings
            for s_id in sentence_ids:
                adjusted_index = s_id - ex_doc_idx_offset
                ex_summary_comparsion_data.append(ex_state_comp_data[adjusted_index])
        
        # end example summary for-loop

        # get the average SBERT embedding of the example summaries
        ex_summary_comparsion_data = np.mean(np.array(ex_summary_comparsion_data), axis=0)

        # list to hold the cosine distance scores
        similairty_scores = []
       
        for test_dat in test_doc_comparsion_data:
            new_score = cosine(test_dat, ex_summary_comparsion_data)
            similairty_scores.append(new_score)
        
        # sort the indicies based on cosine distance scores
        indicies = np.argsort(similairty_scores)
        
        # Add the test document index offset to each index in the results
        indicies = [i + test_doc_idx_offset for i in indicies]
        
        # Get the top-k sentences from the sorted, and index corrected scores
        sentence_subset = indicies[:top_k]

        sentence_subset = [val.item() for val in sentence_subset]

        return sentence_subset