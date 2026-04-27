"""
Readers for the SubSumE user-summary JSONs and synthetic data.

UserDataReader            -- reads ../SubSumE_Data/user_summary_jsons/userInput_*.txt
SyntheticUserDataReader   -- reads a single synthetic-data JSON file.
"""

import json
import os
from collections import defaultdict
from os import listdir
from os.path import isfile, join

import numpy as np
import pandas as pd


class UserDataReader:
    def __init__(self, folder_path, data_csv_path, min_range, max_range):
        self.path = folder_path
        self.userdata_json = self._read_all(self.path, min_range, max_range)
        with open(data_csv_path) as f:
            sep = ';' if ';' in f.readline() else ','
        self.df = pd.read_csv(data_csv_path, sep=sep)

    def _load(self, p):
        with open(p) as f:
            return f.read()

    def _read_all(self, path, min_range, max_range):
        out = []
        for fn in [f for f in listdir(path) if isfile(join(path, f))]:
            if "userInput" not in fn:
                continue
            try:
                num = int(fn.split('_')[1].split('.')[0])
            except (IndexError, ValueError):
                continue
            if min_range <= num < max_range:
                out.append(json.loads(self._load(path + fn)))
        return out

    def read_summaries_keyvalue(self):
        out = []
        for u in self.userdata_json:
            samp = {}
            for s in u['summaries']:
                txt = " ".join(self.df[self.df['sid'] == sid]['sentence'].to_numpy()[0]
                               for sid in s['sentence_ids'])
                samp[s['state_name']] = txt.strip()
            out.append(samp)
        return out

    def read_summaries_list(self):
        sums, ids = [], []
        for u in self.userdata_json:
            tx, ix = [], []
            for s in u['summaries']:
                txt = ""
                sid_list = []
                for sid in s['sentence_ids']:
                    txt += self.df[self.df['sid'] == sid]['sentence'].to_numpy()[0] + " "
                    sid_list.append(sid)
                tx.append(txt.strip())
                ix.append(sid_list)
            sums.append(tx)
            ids.append(ix)
        return sums, ids

    def read_intent_doc(self):
        out = []
        for u in self.userdata_json:
            d = defaultdict(list)
            for s in u['summaries']:
                d[u['intent']].append(s['state_name'])
            out.append(d)
        return out

    def read_example_summaries_sudocu(self):
        return [u['summaries'] for u in self.userdata_json]

    def read_intents(self):
        return list({u['intent'] for u in self.userdata_json})

    def read_usedkeywords_doc(self):
        out = []
        for u in self.userdata_json:
            kws = set()
            for s in u['summaries']:
                kws.update(s.get('used_keywords', []))
            out.append(list(kws))
        return out


class SyntheticUserDataReader:
    """Reader for the synthetic single-topic / multi-topic test JSONs used by Figs. 13–14."""

    def __init__(self, json_path, data_csv_path, min_range, max_range):
        self.path = json_path
        with open(json_path, 'r') as f:
            self.userdata_json = list(json.load(f))
        with open(data_csv_path) as f:
            sep = ';' if ';' in f.readline() else ','
        self.df = pd.read_csv(data_csv_path, sep=sep)

    def read_summaries_list(self):
        sums, ids = [], []
        for u in self.userdata_json:
            txt = ""
            sid_list = []
            for sid in u['sentence_ids']:
                txt += self.df[self.df['sid'] == sid]['sentence'].to_numpy()[0]
                sid_list.append(sid)
            sums.append(txt.strip())
            ids.append(sid_list)
        return sums, ids

    def read_example_summaries_sudocu(self):
        return list(self.userdata_json)
