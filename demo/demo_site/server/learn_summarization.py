import pandas as pd
import numpy as np
import sys
import json
import warnings
warnings.filterwarnings("ignore")

examples = json.loads(sys.argv[1])

df = pd.read_csv("data.csv")
nTopics = 10
topic_sums = np.zeros((len(examples), nTopics))

for i in range(len(examples)):
    ex = examples[i]
    sid = int(ex["state_id"])
    sentence_ids = [int(s) for s in ex["sentence_id"]]

    for topic_id in range(nTopics):
        topic_sums[i, topic_id] = np.sum(
            np.array(
                [
                    np.array(df[df["sid"] == sid]["topic_" + str(topic_id)])[0]
                    for sid in sentence_ids
                ]
            )
        )

topic_min = list(np.min(topic_sums, axis=0))
topic_max = list(np.max(topic_sums, axis=0))

bounds = ""
eps = 1e-4
for i in range(len(topic_min)):
    bounds += str(round(topic_min[i] * 0.9 - eps, 3)) + " " + str(round(topic_max[i] * 1.1 + eps, 3)) + " "
print (bounds)