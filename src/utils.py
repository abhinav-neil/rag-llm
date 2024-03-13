import os
import re
import json
from typing import Literal
from dotenv import load_dotenv
import pandas as pd


def get_env_variable(var_name):
    load_dotenv()
    value = os.environ.get(var_name)
    if value is None:
        raise EnvironmentError(f"Environment variable {var_name} not set.")
    return value


def load_postgres_env_variables():
    """
    Load environment variables for postgres database.
    """
    host = get_env_variable("POSTGRES_HOST")
    port = get_env_variable("POSTGRES_PORT")
    db = get_env_variable("POSTGRES_DB")
    user = get_env_variable("POSTGRES_USER")
    password = get_env_variable("POSTGRES_PASSWORD")

    return host, port, db, user, password


def load_neo4j_env_variables():
    """
    Load environment variables for neo4j database.
    """
    uri = get_env_variable("NEO4J_URI")
    user = get_env_variable("NEO4J_USERNAME")
    password = get_env_variable("NEO4J_PASSWORD")
    db = os.environ.get("NEO4J_DB", "neo4j")

    return uri, user, password, db


def eval_rag_responses(responses_eval_path: str, results_path: str) -> dict:
    """
    Evaluate RAG responses and return metrics dict.
    Args:
        responses_eval_path: Path to the responses_eval.csv file.
        results_path: Path to save the results.
    Returns:
        metrics: Dict with metrics.
    """
    df_responses_eval = pd.read_csv(responses_eval_path, sep=";", index_col="id")
    num_queries_easy = len(df_responses_eval[df_responses_eval["difficulty"] == "easy"])
    num_queries_hard = len(df_responses_eval[df_responses_eval["difficulty"] == "hard"])
    num_queries = len(df_responses_eval)
    num_correct_easy = len(
        df_responses_eval[
            (df_responses_eval["difficulty"] == "easy")
            & (df_responses_eval["correct"] == True)
        ]
    )
    num_correct_hard = len(
        df_responses_eval[
            (df_responses_eval["difficulty"] == "hard")
            & (df_responses_eval["correct"] == True)
        ]
    )
    num_correct = len(df_responses_eval[df_responses_eval["correct"] == True])

    eval_res = {
        "num_queries": num_queries,
        "num_correct": num_correct,
        "num_queries_easy": num_queries_easy,
        "num_correct_easy": num_correct_easy,
        "num_queries_hard": num_queries_hard,
        "num_correct_hard": num_correct_hard,
        "accuracy": num_correct / num_queries,
        "accuracy_easy": num_correct_easy / num_queries_easy,
        "accuracy_hard": num_correct_hard / num_queries_hard,
    }

    with open(results_path, "w") as f:
        json.dump(eval_res, f)

    return eval_res
