from ast import literal_eval
from typing import List, Union
import re
from urllib import response
import numpy as np
from langchain_openai import AzureOpenAIEmbeddings, ChatOpenAI, AzureChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.sql_database import SQLDatabase
from langchain.graphs import Neo4jGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from src.data_utils import Neo4jGraphManager, SQLDBManager
from src.prompt_templates import kg_rag_agent_sys_prompt, sql_rag_agent_sys_prompt


def query_graph(query):
    """
    Query graph using cypher query and return result.
    Args:
    - query (str): cypher query
    """
    ngm = Neo4jGraphManager.from_env()  # instantiate neo4j graph manager
    try:
        result = ngm.graph.query(query)
    except Exception as e:
        result = f"error: {e}"
    return result


def query_db(query):
    """
    Query SQL database using SQL query and return result.
    Args:
    - query (str): SQL query
    """
    dbm = SQLDBManager.from_env()  # instantiate sql db manager
    result = dbm.db.run(query)
    return result


def graph_sim_search(user_query):
    """
    Find similar entities in graph using user query.
    Args:
    - user_query (str): user query
    """
    ngm = Neo4jGraphManager.from_env()  # instantiate neo4j graph manager
    embs_model = AzureOpenAIEmbeddings(
        azure_deployment="text-embedding-ada-002"
    )  # instantiate embeddings model
    matches = []
    embedding = embs_model.embed_query(user_query)
    threshold = 0.75  # similarity threshold
    query = """
        WITH $embedding AS inputEmbedding
        MATCH (n)
        WHERE gds.similarity.cosine(inputEmbedding, n.embedding) > $threshold
        RETURN n, gds.similarity.cosine(inputEmbedding, n.embedding) AS sim
        """
    result = ngm.graph.query(
        query, params={"embedding": embedding, "threshold": threshold}
    )
    for r in result:
        matches.append(
            {"id": r["n"]["pyid"], "name": r["n"]["pylabel"], "sim": r["sim"]}
        )
    # sort matches by similarity
    matches = sorted(matches, key=lambda x: x["sim"], reverse=True)
    return matches


def db_sim_search(user_query, table="pegadata.ppm_work_filtered"):
    """
    Find similar entities in database using user query.
    Args:
    - user_query (str): user query
    - table (str): table name
    """
    dbm = SQLDBManager.from_env()  # instantiate sql db manager
    embs_model = AzureOpenAIEmbeddings(
        azure_deployment="text-embedding-ada-002"
    )  # instantiate embeddings model
    matches = []
    query_emb = embs_model.embed_query(user_query)
    threshold = 0.8  # similarity threshold
    query = f"SELECT pyid, pylabel, embeddings FROM {table};"
    result = dbm.db.run(query)
    result = literal_eval(result)  # convert string to list
    for row in result:
        id, label, emb = row
        emb = np.array(emb)  # convert the embedding string to a numpy array

        # calculate cosine similarity
        cos_sim = np.dot(query_emb, emb) / (
            np.linalg.norm(query_emb) * np.linalg.norm(emb)
        )

        if cos_sim > threshold:
            matches.append({"id": id, "name": label, "sim": cos_sim})

    # sort matches by similarity
    matches = sorted(matches, key=lambda x: x["sim"], reverse=True)
    return matches


class GraphQueryAgent:
    def __init__(
        self,
        graph: Neo4jGraph,
        llm: Union[ChatOpenAI, AzureChatOpenAI],
    ):
        self.graph = graph  # neo4j graph
        self.llm = llm  # llm
        # define tools
        self.tools = [
            Tool(
                name="query_graph",
                func=query_graph,
                description="""
                    Query graph using cypher query and return result.
                    Args:
                    - query (str): cypher query
                """,
            ),
            Tool(
                name="graph_sim_search",
                func=graph_sim_search,
                description="""
                    Find similar entities in graph using user query.
                    Args:
                    - user_query (str): user query
                """,
            ),
        ]

        # construct prompt
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", kg_rag_agent_sys_prompt),
                ("user", "input: {input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
                ("system", "\n\n"),
            ]
        )

        # define agent
        self.agent = create_openai_tools_agent(self.llm, self.tools, self.prompt)
        self.agent_exec = AgentExecutor.from_agent_and_tools(
            agent=self.agent, tools=self.tools, verbose=True
        )

    def run(self, query):
        """
        Run agent with user query.
        Args:
        - query (str): user query
        """
        result = self.agent_exec.invoke(
            {"input": query, "schema": self.graph.schema, "tools": self.tools}
        )
        # parse the output
        if "Final Answer:" in result["output"]:
            split_output = re.split("(?i)Final Answer:", result["output"])
            response = (
                split_output[1].strip() if len(split_output[1].strip()) > 1 else "N/A"
            )
        else:
            response = result["output"]
        return response


class SQLQueryAgent:
    """SQL-RAG agent using tools."""

    def __init__(
        self,
        db: SQLDatabase,
        llm: Union[ChatOpenAI, AzureChatOpenAI],
    ):
        self.db = db  # sql db
        self.llm = llm  # llm

        # define tools
        self.tools = [
            Tool(
                name="query_db",
                func=query_db,
                description="""
                    Query SQL db using SQL query and return result.
                    Args:
                    - query (str): sql query
                """,
            ),
            Tool(
                name="db_sim_search",
                func=db_sim_search,
                description="""
                    Find similar entities in database using user query.
                    Args:
                    - user_query (str): user query
                    - table (str): table name
                """,
            ),
        ]

        # construct prompt
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", sql_rag_agent_sys_prompt),
                ("user", "input: {input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
                ("system", "\n\n"),
            ]
        )

        # define agent
        self.agent = create_openai_tools_agent(self.llm, self.tools, self.prompt)
        self.agent_exec = AgentExecutor.from_agent_and_tools(
            agent=self.agent, tools=self.tools, verbose=True
        )

    def run(self, query: str):
        """Run agent with user query."""
        result = self.agent_exec.invoke(
            {"input": query, "schema": self.db.table_info, "tools": self.tools}
        )
        # parse the output
        if "Final Answer:" in result["output"]:
            split_output = re.split("(?i)Final Answer:", result["output"])
            response = (
                split_output[1].strip() if len(split_output[1].strip()) > 1 else "N/A"
            )
        else:
            response = result["output"]
        return response
