"""
Turn Count Verifier
-------------------
This script verifies the number of conversation turns in generated conversation files to ensure data consistency and correctness before evaluation.

Dependencies:
    - os, pandas
"""

import os

import pandas as pd

eval_file = "VLMEvalPipeline/Evals/EvalsMainExp.tsv"


df = pd.read_csv(
    eval_file,
    sep="\t",
    encoding="utf-8",
)
orig_num_turns = df["NumTurns"]
actual_num_turns = df["Query"].apply(lambda x: len(eval(eval(x)["GenConv"])))
# Verify that the number of turns in the query matches the number of turns in the conversation
for orig, actual in zip(orig_num_turns, actual_num_turns):
    assert (
        orig == actual
    ), f"Original number of turns: {orig}, Actual number of turns: {actual}"
print("All number of turns match!")
