from typing import List, Union
from langchain_openai import AzureOpenAIEmbeddings, ChatOpenAI, AzureChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.graphs import Neo4jGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from src.data_utils import Neo4jGraphManager
from src.prompt_templates import kg_rag_agent_sys_prompt

def query_graph(query):
    '''
    Query graph using cypher query and return result.
    Args:
    - query (str): cypher query
    '''
    ngm = Neo4jGraphManager.from_env()  # instantiate neo4j graph manager
    result = ngm.graph.query(query)
    return result

def similarity_search(user_query):
    '''
    Find similar entities in graph using user query.
    Args:
    - user_query (str): user query
    '''
    ngm = Neo4jGraphManager.from_env()  # instantiate neo4j graph manager
    embs_model = AzureOpenAIEmbeddings(azure_deployment="text-embedding-ada-002") # instantiate embeddings model
    matches = []
    embedding = embs_model.embed_query(user_query)
    threshold = 0.8   # similarity threshold 
    query = '''
            WITH $embedding AS inputEmbedding
            MATCH (n)
            WHERE gds.similarity.cosine(inputEmbedding, n.embedding) > $threshold
            RETURN n
            '''
    result = ngm.graph.query(query, params={'embedding': embedding, 'threshold': threshold})
    for r in result:
        id = r['n']['pyid']
        matches.append({
            "id": id,
            "name":r['n']['pylabel']
        })
    return matches

class GraphQueryAgent():
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
                description='''
                    Query graph using cypher query and return result.
                    Args:
                    - query (str): cypher query
                '''
            ),
            Tool(
                name="similarity_search",
                func=similarity_search,
                description='''
                    Find similar entities in graph using user query.
                    Args:
                    - user_query (str): user query
                '''
            )
    ]

        # construct prompt
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    kg_rag_agent_sys_prompt,
                ),
                ("user", "input: {input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        # define agent
        self.agent = create_openai_tools_agent(self.llm, self.tools, self.prompt)
        self.agent_exec = AgentExecutor.from_agent_and_tools(agent=self.agent, tools=self.tools, verbose=True)
        
    def run(self, query):
        '''
        Run agent with user query.
        Args:
        - query (str): user query
        '''
        result = self.agent_exec.invoke({"input": query, "schema": self.graph.schema, "tools": self.tools})
        return result