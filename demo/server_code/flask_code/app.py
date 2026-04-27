from __future__ import division, unicode_literals
from asyncio import constants 
from flask import Flask, request, jsonify, make_response, render_template, session
import pandas as pd
import numpy as np
import json
import random
import re
from os.path import join
import http
from ..Models.SD_NNBS_BS_RTL import SuDocu_NNBS_BS_RTL
from ..Models.SD_NNBS_BS_RTL_RELAX import SuDocu_NNBS_BS_RTL_Relax
from ..Models.SBERT import SBERT
import email.utils
from logging import FileHandler,WARNING

import os
import secrets
import sys

app = Flask(__name__, static_url_path='',
            static_folder='web/static',
            template_folder='web/templates')

file_handler = FileHandler('errorlog.txt')
file_handler.setLevel(WARNING)

# Set FLASK_SECRET_KEY in your environment for production deployments.
# A random fallback is generated for local development so sessions still work.
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or secrets.token_hex(32)

data_path = "data/data_ctm.csv"

shared_docs_path = "data/"

logging_data_path = "../User_Study_Data/"
nTopics = 10


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)

@app.route('/')
def home_page():
    return render_template("consent.html")

@app.route('/preStudy')
def preStudy():
    return render_template("preStudy.html")

@app.route('/tutorialVideo-systemU')
def tutorialVideo_sudocu():
    return render_template("tutorialVideo_sudocu.html")

@app.route('/tutorialVideo-systemV')
def tutorialVideo_sbert():
    return render_template("tutorialVideo_sbert.html")

@app.route('/tutorial-systemU')
def skippable_tutorial_sudocu():
    return render_template("skip_tutorial_sudocu.html")

@app.route('/tutorial-systemV')
def skippable_tutorial_sbert():
    return render_template("skip_tutorial_sbert.html")

@app.route('/systemU')
def sudocu_A():
    a = 0
    session["taskOrder"] = a 
    return render_template("sudocu_A.html")

@app.route('/postTask-systemU')
def postTaskSuDoCuA():
    return render_template("postTask-sudocuA.html")

@app.route('/systemV')
def sbert():
    a = 1
    session["taskOrder"] = a 
    return render_template("sbert_A.html")

@app.route('/postTask-systemV')
def postTaskSBERT():
    return render_template("postTask-sbert.html")

@app.route('/postStudy')
def postStudy():
    return render_template("postStudy.html")

@app.route('/endPage')
def endPage():
    return render_template("endPage.html")

def generate_random_states():
    cur_value = random.randint(0, 49)
    data_path_ = 'data/state_splits/state_split_' + str(int(cur_value)) + '.json'
    
    file = open(data_path_)
    data = json.load(file)
    cur_state_names = []
    cur_state_ids = []
    for key, value in data['split_one'].items():
        cur_state_names.append(key)
        cur_state_ids.append(value)
    return cur_state_names, cur_state_ids

@app.route('/get_states')
def get_states():
    sudocu_states = []
    sbert_states = []
    sudocu_state_names, sudocu_state_ids = generate_random_states()
    df_states = pd.read_csv(data_path, sep=";", dtype= {"pid":"int64", "name":"object","sid":"int64", "sentence":"object",
                          "score":"float64", "topic_0":"float64", "topic_1":"float64",
                          "topic_2":"float64", "topic_3":"float64", "topic_4":"float64",
                          "topic_5":"float64", "topic_6":"float64", "topic_7":"float64",
                          "topic_8":"float64", "topic_9":"float64"})
    #a list of unique state names
    state_names = df_states.name.unique().tolist()
    #a list of unique state ids
    state_ids = df_states.pid.unique().tolist()

    for s_name, s_id in zip(state_names, state_ids):
        if s_name in sudocu_state_names:
            sudocu_states.append({'state_id':s_id, 'state_name':s_name})
        else:
            #states not found in the randomly generated states list are considered as sbert states
            sbert_states.append({'state_id':s_id, 'state_name':s_name})
    return sudocu_states, sbert_states

sudocu_states, sbert_states = get_states()
@app.route('/get_states_sudocu')
def get_states_sudocu():
    cur_states = sudocu_states
    response = jsonify(cur_states)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/get_states_sbert')
def get_states_sbert():
    cur_states = sbert_states
    response = jsonify(cur_states)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/get_sentences')
def get_sentences():
    sentences = []
    df_states = pd.read_csv(data_path, sep=";", dtype= {"pid":"int64", "name":"object","sid":"int64", "sentence":"object",
                          "score":"float64", "topic_0":"float64", "topic_1":"float64",
                          "topic_2":"float64", "topic_3":"float64", "topic_4":"float64",
                          "topic_5":"float64", "topic_6":"float64", "topic_7":"float64",
                          "topic_8":"float64", "topic_9":"float64"})
    requested_pid = int(request.args.get('state_id'))
    #list of sentences for the requested pid 
    state_sentences = df_states[df_states['pid'] == requested_pid].sentence.tolist()
    #list of sentence ids for the requested pid
    sentence_ids = df_states[df_states['pid'] == requested_pid].sid.tolist()

    for s_sen, s_id in zip(state_sentences, sentence_ids):
        sentences.append({'sentence_id':s_id, 'text':s_sen})
    response = jsonify(sentences)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/learn_summarization', methods=['POST'])
def learn_summarization():
    bounds = ""

    examples = request.form.get('example')
    examples_json =json.loads(examples)
    #sudocu model
    summerizer_model = SuDocu_NNBS_BS_RTL_Relax(data_path, shared_docs_path, nTopics)

    bounds = summerizer_model.get_bounds(examples_json)

    response = jsonify(bounds[0].tolist())
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response
    
@app.route('/topic_keyword_appearances', methods=['POST'])
def topic_keyword_appearances():
    response = {}
    response_dict = {}
    req = int(request.form.get('modified'))
    if req == 0:
        with open(join(shared_docs_path, "StateKeywords/all_states.txt"), 'r') as f:
            response_dict['topics'] = json.loads(f.read())
        response = jsonify(response_dict['topics'])
    else:
        examples = request.form.get('example')
        examples_json =json.loads(examples)

        f = open(join(shared_docs_path, "topic_words_json.txt"))
        topicWordList = json.loads(f.read())["words"]
        topicWordListofSets = [set(ele) for ele in topicWordList]

        appearances = []
        storageSet = set()
        for topic_id in range(len(topicWordListofSets)):
            appearancesDict = {}
            for summary in examples_json:
                for word in summary.split():
                    filteredWord = re.sub(r"[^a-zA-Z0-9]+", '', word).lower()
                    if filteredWord in topicWordListofSets[topic_id]:
                        if filteredWord in appearancesDict:
                            appearancesDict[filteredWord] += 1
                        else:
                            wordInDict = False
                            if filteredWord in storageSet:
                                wordInDict = True
                            if wordInDict is False:
                                appearancesDict[filteredWord] = 1  
                            else:
                                wordInDict = True
                            storageSet.add(filteredWord)
            #######################################FILL FEATURE#######################################                
            for i in topicWordList[topic_id]:
                if len(appearancesDict) < 10:
                    if i not in appearancesDict:
                        appearancesDict[i] = 0
                else:
                    break
            ##########################################################################################
            sorted_appDict = sorted(appearancesDict.items(), key=lambda kv: kv[1], reverse=True)
            appearances.append({
                "keywords":  [{'word': i[0], 'count': i[1]} for i in sorted_appDict][:10],
                "topic_id": topic_id,
            })
        response = jsonify(appearances)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/get_summary_initial', methods=['POST'])
def get_summary_initial():
    response_dict = {}
    log_dict = {}
    examples = request.form.get('example')
    bounds = request.form.get('bounds')
    state_name = request.form.get('state_name')
    state_id = int(request.form.get('state_id'))

    # load all of the json stuff
    examples_json = json.loads(examples)
    bounds_json = json.loads(bounds)

    # used for logging
    userID = request.form.get('user_id')

    if (len(bounds_json) < 1):
        bounds_json = None

    summerizer_model = SuDocu_NNBS_BS_RTL_Relax(data_path, shared_docs_path, nTopics)

    summary_txt, summary_indicies = summerizer_model.get_predicted_summary(userID, state_name, examples_json, 0, bounds_json)

    response_dict['summary'] = summary_txt
    response_dict['summary_indicies'] = summary_indicies

    response = jsonify(response_dict)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


#summary returned after the user clicks on the 'generate summary' button 
@app.route('/get_summary', methods=['POST'])
def get_summary():
    taskOrder0 = session.get("taskOrder",None) == 0 
    response_dict = {}
    log_dict = {}
    examples = request.form.get('example')
    bounds = request.form.get('bounds') if taskOrder0 else None
    state_name = request.form.get('state_name')
    state_id = int(request.form.get('state_id'))
    first_gen = request.form.get('first_gen')

    if first_gen == "true":
        first_gen = True
    else:
        first_gen = False

    # used for logging
    userID = request.form.get('user_id')

    # load all of the json stuff
    examples_json = json.loads(examples)
    bounds_json = json.loads(bounds) if bounds else None

    if taskOrder0:
        # alg. two relaxation stuff
        center_slopes = request.form.get("center_slopes")
        center_offsets = request.form.get("center_offsets")
        bound_slopes = request.form.get("bound_slopes")
        bound_offsets = request.form.get("bound_offsets")
        r_maxs = request.form.get("r_maxs")
        slider_val_diffs = request.form.get("slider_diffs")
        slider_vals = request.form.get("slider_vals")
        prev_slider_vals = request.form.get("prev_slider_vals")
        stable_bounds = request.form.get("stable_bounds")

        # json stuff for alg. 2 relaxation
        center_slopes_json = json.loads(center_slopes)
        center_offsets_json = json.loads(center_offsets)
        bound_slopes_json = json.loads(bound_slopes)
        bound_offsets_json = json.loads(bound_offsets)
        r_maxs_json = json.loads(r_maxs)
        slider_val_diffs_json = json.loads(slider_val_diffs)
        slider_vals_json = json.loads(slider_vals)
        prev_slider_vals_json = json.loads(prev_slider_vals)
        stable_bounds_json = json.loads(stable_bounds)

        # make a disctionary (to pass a single param)
        slider_alg_vals = {}
        slider_alg_vals['center_slopes'] = center_slopes_json
        slider_alg_vals['center_offsets'] = center_offsets_json
        slider_alg_vals['bound_slopes'] = bound_slopes_json
        slider_alg_vals['bound_offsets'] = bound_offsets_json
        slider_alg_vals['r_maxs'] = r_maxs_json
        slider_alg_vals['slider_val_diffs'] = slider_val_diffs_json
        slider_alg_vals['slider_vals'] = slider_vals_json
        slider_alg_vals['prev_slider_vals'] = prev_slider_vals_json
        slider_alg_vals['stable_bounds'] = stable_bounds_json
    

    summerizer_model = SuDocu_NNBS_BS_RTL_Relax(data_path, shared_docs_path, nTopics) if taskOrder0 else SBERT(
        data_path, shared_docs_path, nTopics)

    if taskOrder0:
        summary_txt, summary_indicies = summerizer_model.get_predicted_summary_relax(userID, state_name, examples_json, 0, bounds_json, first_gen, slider_alg_vals)
    else:
        summary_txt, summary_indicies = summerizer_model.get_predicted_summary(state_name, examples_json, 0, bounds_json, first_gen)

    # if this is the first time being solved (no sliders) we want to return the generated bounds
    if first_gen and taskOrder0:
        response_dict['bounds'] = summerizer_model.get_utilized_bounds()
    
    if first_gen == False and taskOrder0:
        response_dict['slider_vals'] = summerizer_model.get_utilized_slider_values()
    
    #if no optimal solution
    if (taskOrder0 and "def_sum" in summary_txt[:10]):
        response_dict['default'] = True
        #remove def_sum from the summary
        response_dict['summary'] = summary_txt[8:] 
    else:
        response_dict['default'] = False
        response_dict['summary'] = summary_txt 

    response_dict['summary_indicies'] = summary_indicies

    # add in bounds used to generate summary

    response = jsonify(response_dict)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/get_topic_keywords')
def get_topic_keywords():
    response_dict = {}
    requested_pid = int(request.args.get('state_id'))

    if (requested_pid == -1):
        with open(join(shared_docs_path, "StateKeywords/all_states.txt"), 'r') as f:
            response_dict['topics'] = json.loads(f.read())
    else:
        with open(join(shared_docs_path, "StateKeywords/state_{}.txt".format(requested_pid)), 'r') as f:
            response_dict['topics'] = json.loads(f.read())

    response = jsonify(response_dict)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/log_interaction', methods=['POST'])
def log_interaction():
    userID = request.form.get('user_id')
    content = json.loads(request.form.get('content'))

    file_path = join(logging_data_path, userID + "_interaction_log.csv")

    f=open(file_path, 'a+')
    for interaction_log in content:
        f.write(interaction_log)
    f.close()

    response = make_response('', http.HTTPStatus.NO_CONTENT,)
    response.headers.add('Access-Control-Allow-Origin', '*')
    
    return response