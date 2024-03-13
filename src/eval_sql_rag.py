"""Evaluate LLM RAG on SQL DB with sample queries"""

import os
import pandas as pd
from langchain_openai import ChatOpenAI, AzureChatOpenAI

from src.utils import *
from src.data_utils import SQLDBManager
from src.tools import SQLQueryAgent
from src.config import *


def main():
    ## Prepare & init DB
    dbm = SQLDBManager.from_env(
        schema=TABLE_SCHEMA, include_tables=[TABLE_NAME]
    )  # instantiate SQLDBManager
    llm = AzureChatOpenAI(
        model=OPENAI_LLM_VERSION, max_tokens=MAX_TOKENS, temperature=TEMPERATURE
    )  # instantiate llm

    # set db variables
    src_table = f"{TABLE_SCHEMA}.{TABLE_NAME}"
    data_table = f"{src_table}_filtered"

    dbm = SQLDBManager.from_env()  # instantiate SQLDBManager

    # filter data table and create new
    dbm.filter_table(src_table, REQ_COLS_PATH, TABLE_PRIMARY_KEY, overwrite=True)

    # clean html
    dbm.clean_html(data_table, [TEXT_COL], TABLE_PRIMARY_KEY)  # clean html

    # create embeddings
    dbm.embed_objs(
        f"{TABLE_SCHEMA}.{TABLE_NAME}",
        cols_to_embed=COLS_TO_EMBED,
        pk=TABLE_PRIMARY_KEY,
    )

    # eval on test set
    df_queries = pd.read_csv(TEST_QUERIES_PATH, sep=";", index_col="id")
    responses = {}
    dqa = SQLQueryAgent(dbm.db, llm)  # instantiate db query agent

    # iter thru queries and generate responses
    for qid, row in df_queries.iterrows():
        query = row["query"]
        try:
            result = dqa.run(query=query)
            responses[qid] = result
        except Exception as e:
            print(f"error: {e}")

    # save responses to csv
    df_responses = pd.DataFrame.from_dict(
        responses, orient="index", columns=["response"]
    )
    responses_path = SQL_RESPONSES_EVAL_PATH
    os.makedirs(os.path.dirname(responses_path), exist_ok=True)
    with open(responses_path, "w") as f:
        df_responses.to_csv(f, sep=";")
    # compute accuracy of responses
    eval_rag_responses(responses_path, SQL_RESULTS_PATH)


if __name__ == "__main__":
    main()
