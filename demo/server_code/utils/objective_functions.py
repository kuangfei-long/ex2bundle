import pandas as pd
import numpy as np
from os.path import join
import json
import math
import re
import nltk
import itertools
from scipy.spatial.distance import cosine, jensenshannon
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.preprocessing import minmax_scale
import string


class Objective_Function_Wrapper:
    def __init__(self, data_path, shared_docs, nTopics):
        self.data_path = data_path
        self.shared_docs_path = shared_docs
        
        with open(join(self.shared_docs_path, "state_indices.txt")) as f:
            file = f.read()
            f.close()
        self.doc_indicies = json.loads(file)
        
        self.nTopics = nTopics
        
        self.topic_names = ["topic_" + str(i) for i in range(self.nTopics)]
        self.epsilon = 0.00001
        self.df = pd.read_csv(data_path, sep=";")


    ###
    #    Helper function to clean collections of sentences before use by the
    #        the TFIDF and Count Vectorizers
    #    args: sentences -> str array, collecion of sentences
    #    
    #    returns: sentences -> str array, collection cleaned sentences
    ###    
    def cleanSentences(self, sentences):
        stopwords2 = [
            line.strip().lower()
            for line in open(self.shared_docs_path + "stopwords.txt").readlines()
            if line.strip() != ""
        ]
        
        # Convert each article to all lower case
        sentences = [str(sentence).lower() for sentence in sentences]
        
        # Strip all punctuation from each article
        # This uses str.translate to map all punctuation to the empty string
        table = str.maketrans('', '', string.punctuation)
        sentences = [sentence.translate(table) for sentence in sentences]
        
        # Convert all numbers in the article to the word 'num' using regular expressions
        sentences = [re.sub(r'\d+', 'num', sentence) for sentence in sentences]
        
        # Create stopwords list, convert to a set for speed
        stopwords = set(nltk.corpus.stopwords.words('english') + stopwords2)
        sentences = [[word for word in sentence.split() if word not in stopwords] for sentence in sentences]
        
        # stem the input (almost the same as leemanizing)
        stemmer = nltk.stem.PorterStemmer()
        sentences = [" ".join([stemmer.stem(word) for word in sentence]) for sentence in sentences]
        # print the first article as a running example
        
        return sentences

    ###
    #    generate the SBERT, Example Summary Merit Cosine Similarity Score
    #    args: state -> str, state doc to be summarized
    #          sentence_ids -> int array, sentence ids for data CSV
    #    
    #    returns: merit_scores -> double array, cosine simialirty scores  
    ###    
    def calculateBSMeritScore(self, sentence_ids, target_doc, example_embedding):

        
        # calculate merit scores of candidiate sentences
        npz_path = join(self.shared_docs_path, "StateDocuments/", target_doc + "sudocu.npz")
        data = np.load(npz_path)
        doc_bert_data = data['embedding']

        # array to hold bert merit scores 
        merit_scores = []

        state_start_index = self.doc_indicies[target_doc][0]
        # loop over sentences
        for sen_id in sentence_ids:
            adjusted_index = sen_id - state_start_index
            sentence_embedding = doc_bert_data[adjusted_index]
            new_score = 1 - cosine(sentence_embedding, example_embedding)
            merit_scores.append(new_score)

        merit_scores = np.array(merit_scores)
        
        return merit_scores


    ###
    #    Calculate the Normalized TF-IDF scores for the target sentences
    #    args: sentences_target -> str array, the actual string target sentences
    #    
    #    returns: tfidf_scores -> double array, normalized TFIDF scores 
    ###    
    def calculateNormalizedTFIDF(self, sentences_target, example_sentences):

        tfidfvectorizer = TfidfVectorizer(analyzer='word',stop_words= 'english')
        
        # fit an Sklearn TFIDF vectorizer on the example sentences
        tfidfvectorizer.fit(example_sentences)

        # score the target sentences based on the TF values learned from the 
        #    example summaries
        tfidf_scores = tfidfvectorizer.transform(sentences_target).toarray()
        
        # get the sentence_wise sum of the target sentences
        #     TFIDF scores
        tfidf_scores = np.sum(tfidf_scores, axis=1)

        # normalize tfidf scores
        #    first find the max value
        max_val = np.max(tfidf_scores)
        
        # then divide all values by the max_val
        tfidf_scores = tfidf_scores / max_val
        
        return tfidf_scores.squeeze()

    ###
    #    Calculate the Normalized Log Probability Ratio Score
    #    args: sentences_target -> str array, the actual string target sentences
    #    
    #    returns: log_prod_ratio_scores -> double array, normalized LPR scores  
    ###    
    def calculateNormalizedLPR(self, sentences_target, example_sentences):
        countvectorizer = CountVectorizer(analyzer='word',stop_words= 'english')
        
        # combine the two sets of sentences
        total_sentences = list(itertools.chain(sentences_target, example_sentences))
       
        # fit the count vectorizer on both the example and target sentences
        countvectorizer.fit(total_sentences)

        # find the document-count matrix for the target sentences and example sentences
        example_counts_mat = countvectorizer.transform(example_sentences).toarray()
        target_counts_mat = countvectorizer.transform(sentences_target).toarray()

        # get the feature(word)-wise counts for example and target
        example_counts = np.sum(example_counts_mat, axis=0)
        target_counts = np.sum(target_counts_mat, axis=0)

        # get the total number of features (or words in each document) 
        example_total = np.sum(example_counts)
        target_total = np.sum(target_counts)

        # get the feature(word)-wise probabilities for example and target documents
        example_probs = example_counts / example_total
        target_probs = target_counts / target_total

        # array to hold the log-ratios of the word probabilities
        log_prod_ratio_scores = []

        # iterate over every row (sentence) in the target doc-count matrix
        for row in target_counts_mat:
            # get the induicies of the words contained in this sentence
            #     i.e. non-zero entries in the count row 
            non_zero_indicies = np.nonzero(row)[0]

            # the sentence score associated with this sentence
            sentence_score = 0

            # loop over all the non-zero indicies
            for idx in non_zero_indicies:
                idx_value = 0.0

                # calculate the probability ratio between the summary and target document
                # + epsilon to in numerator to avoid 1/0 error, denominator to avoid zero
                prob_ratio = (example_probs[idx] + self.epsilon) / (target_probs[idx] + self.epsilon) 

                if prob_ratio != 0:
                    # take the base-10 log of the probability ratio 
                    log_prob_r = math.log10(prob_ratio)
                    
                    # we are only using negative scores to guide the ILP away from bad sentences
                    if log_prob_r < 0:
                        idx_value = log_prob_r 
                
                # add the score for this index to the sentences total score 
                sentence_score += idx_value

            # add this sentences score to the total list
            log_prod_ratio_scores.append(sentence_score)

        # normalize the negative values to between 0 and 1. Using min/max
        #     normalizer makes the most negative values zero or near zero
        #     so we subtract by one to properly peanlize the sentences
        log_prod_ratio_scores = np.array(log_prod_ratio_scores)       
        log_prod_ratio_scores = minmax_scale(log_prod_ratio_scores) - 1
        
        return log_prod_ratio_scores

    ###
    #    Helper function to calculate a setences Rouge Scores w.r.t.
    #           a collection of example summaires
    #    args: sentences -> str array, collecion of sentences
    #            rouge_num -> 0 : rouge1, 1: rouge2, 2: rougeL 
    #    
    #    returns: all_scores -> double array, collection sentence scores
    ###    
    def rougeObjective(self, target_sentences, example_sentences, rouge_num):
        # create a "super" summary which is simply all of the sentences
        #     from all of the example summaires joined together
        all_examples = " ".join(example_sentences)
        
        # list to hold the scores for each sentence
        all_scores = []
        
        for sentence in target_sentences:
            scores = self.eval_scorer.compareScore(sentence, all_examples)
            
            # we are using Rouge-1 F-1 objective currently
            all_scores.append(scores[0][rouge_num])
            
        return np.array(all_scores)


    ###
    #    Helper function to the mean and standard deviation of the topic scores
    #        of the sentences in the example summaries both among the sentences
    #        in the summaries as well as the summaries as a whole
    ### 
    def get_mean_stddev(self, example_summaires):
        # get the names for all the topic scores
        topic_names = ['topic_' + str(i) for i in range(self.nTopics)]
        
        # instantiate a numpy array to hold the topic scores
        #     for every sentence in every summary
        topic_scores_sentence = []
        topic_scores_examples = []

        # iterate over every example summary
        for i in range(len(example_summaires)):
            example_topics = []
            # get the example currently being processed
            ex = example_summaires[i]
            
            # get all the sentence id's for this summary
            sid = int(ex["state_id"])
            sentence_ids = [int(s) for s in ex["sentence_ids"]]

            # iterate over every sentence and add it's topic score distribution
            #     to the list of topic scores
            for sid in sentence_ids:
                sid_topic_scores = self.df[self.df["sid"] == sid][topic_names].to_numpy()
                topic_scores_sentence.append(sid_topic_scores)
                example_topics.append(sid_topic_scores)

            example_topic_sum = np.sum(np.array(example_topics), axis=0)
            topic_scores_examples.append(example_topic_sum)
                
        topic_scores_sentence = np.array(topic_scores_sentence)
        topic_scores_examples = np.array(topic_scores_examples)
                
        # get the min and max of every topic from across all the summariess
        topics_mean = np.mean(topic_scores_sentence, axis=0)
        topics_stddev = np.std(topic_scores_sentence, axis=0)

        topics_mean_ex = np.mean(topic_scores_examples, axis=0)
        topics_stddev_ex = np.std(topic_scores_examples, axis=0)
        
        # check that the mean and stddev array are 1-D
        assert topics_mean.shape[0] == 1 and topics_stddev.shape[0] == 1, "topic mean or stddev not 1-D"
        
        # check that the mean and stddev array are of proper length
        assert topics_mean.shape[1] == self.nTopics and topics_stddev.shape[1] == self.nTopics, "len topic mean or stddev not not nTopics"

        # check that the mean and stddev array are 1-D
        assert topics_mean_ex.shape[0] == 1 and topics_stddev_ex.shape[0] == 1, "topic mean or stddev not 1-D"
        
        # check that the mean and stddev array are of proper length
        assert topics_mean_ex.shape[1] == self.nTopics and topics_stddev_ex.shape[1] == self.nTopics, "len topic mean or stddev not not nTopics"
            
        return (topics_mean.squeeze(), topics_stddev.squeeze(), topics_mean_ex.squeeze(), topics_stddev_ex.squeeze()) # end of get_mean_stddev() method

    ###
    #    Helper function to return the average SBERT embedding of the example summaries
    ### 
    def get_ex_embedding(self, example_summaires):
        # array to hold bert embeddins for all the sentences
        bert_embeddings = []

        # iterate over every example summary
        for ex in example_summaires:
            doc = ex['state_name']
            data = np.load(join(self.shared_docs_path, "StateDocuments/", doc + "sudocu.npz"))
            doc_bert = data['embedding']
            
            doc_start_index = self.doc_indicies[doc][0]
            # get the sentence ids
            sentence_ids = [int(s) for s in ex["sentence_ids"]]

            # iterate over every sentence and add it's topic score distribution
            #     to the list of topic scores
            for sid in sentence_ids:
                adjusted_sid = sid - doc_start_index
#                 print(state_bert[adjusted_sid])
                bert_embeddings.append(doc_bert[adjusted_sid])
            
        bert_embeddings = np.array(bert_embeddings)
        
        avg_ex_embed = np.mean(bert_embeddings, axis=0)
            
        return avg_ex_embed
    

    ###
    #    Helper function to return the actual sentences from the example summaries
    ### 
    def get_ex_sentences(self, example_summaires):
        # get the sentences from the example summaries to train the TFIDF vectorizer
        sentences_example = []

        # loop over the example summaries
        for exm_sum in example_summaires:
            sentence_ids = [int(s) for s in exm_sum["sentence_ids"]]

            for s_id in sentence_ids:
                sentences_example.append(self.df[self.df["sid"] == s_id]["sentence"].to_numpy()[0])

            
        return sentences_example

    