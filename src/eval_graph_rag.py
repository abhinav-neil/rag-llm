"""Evaluate LLM RAG on Graph DB with sample queries"""

import os
import pandas as pd
from langchain_openai import ChatOpenAI, AzureChatOpenAI

from src.utils import *
from src.data_utils import Neo4jGraphManager
from src.tools import GraphQueryAgent
from src.config import *


def main():
    ngm = Neo4jGraphManager.from_env()  # instantiate neo4j graph manager
    ngm.from_table(
        f"{TABLE_SCHEMA}.{TABLE_NAME}", reset=True
    )  # create graph from table

    # embed graph objects
    ngm.embed_objs()

    # use agent w tools to query graph
    llm = AzureChatOpenAI(
        model=OPENAI_LLM_VERSION, max_tokens=MAX_TOKENS, temperature=TEMPERATURE
    )  # instantiate llm

    # eval on test set
    df_queries = pd.read_csv(TEST_QUERIES_PATH, sep=";", index_col="id")
    responses = {}
    gqa = GraphQueryAgent(ngm.graph, llm)  # instantiate graph query agent

    # iter thru queries and generate responses
    for qid, row in df_queries.iterrows():
        query = row["query"]
        try:
            result = gqa.run(query)
            responses[qid] = result
            print(result)
        except Exception as e:
            print(f"error: {e}")

    # save responses to csv
    df_responses = pd.DataFrame.from_dict(
        responses, orient="index", columns=["response"]
    )
    responses_path = GRAPH_RESPONSES_EVAL_PATH
    os.makedirs(os.path.dirname(responses_path), exist_ok=True)
    with open(responses_path, "w") as f:
        df_responses.to_csv(f, sep=";")
    # compute accuracy of responses
    eval_res = eval_rag_responses(GRAPH_RESPONSES_EVAL_PATH, GRAPH_RESULTS_PATH)


if __name__ == "__main__":
    main()
