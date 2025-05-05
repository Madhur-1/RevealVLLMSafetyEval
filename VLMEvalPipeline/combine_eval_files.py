"""
Evaluation File Combiner
------------------------
This script combines multiple evaluation result files into a single consolidated file for further analysis or reporting. It is typically used after running batch evaluations across different models or harm categories.

Dependencies:
    - os, pandas
"""

import csv
import os

import pandas as pd

eval_dir = "VLMEvalPipeline/EvalsTextPorted/"
save_file_path = "VLMEvalPipeline/Evals/EvalsTextPorted.tsv"
if os.path.exists(save_file_path):
    os.remove(save_file_path)

comb_df = pd.DataFrame()
for dataset_name in os.listdir(eval_dir):
    if dataset_name.endswith(".tsv"):
        df = pd.read_csv(
            eval_dir + dataset_name, sep="\t", encoding="utf-8", header=None
        )
        print("Before removing duplicates:", len(df))
        df_new = df.drop_duplicates(subset=[0], keep="first")
        print("After removing duplicates:", len(df_new))
        df_new.columns = [
            "Index",
            "HarmScore",
            "HarmResponse",
            "RefusalScore",
            "RefusalResponse",
            "HarmType",
            "EvalConv",
            "Query",
        ]
        df_new["ModelName"] = dataset_name.split("_")[0]
        df_new["NumTurns"] = df_new["Query"].apply(lambda x: eval(x)["NumTurns"])
        comb_df = pd.concat([comb_df, df_new])


comb_df.to_csv(
    save_file_path,
    sep="\t",
    index=False,
    quoting=csv.QUOTE_NONE,
    encoding="utf-8",
)
