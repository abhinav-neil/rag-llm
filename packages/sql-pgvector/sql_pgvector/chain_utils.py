import json
import re
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from sql_pgvector.prompt_templates import postgresql_template, sql_rag_template

# load schema config
with open("src/db_config.json", "r") as f:
    db_config = json.load(f)     

class RAGChainManager():
    '''Class for managing RAG chains'''
    def __init__(self, db, llm, embs_model):
        self.db = db
        self.llm = llm
    
    def get_schema(self, _):
        # get schema of data table
        return self.db.get_table_info([db_config['data_table'].split('.')[1]])
       
    def replace_brackets(self, match):
        words_inside_brackets = match.group(1).split(", ")
        embedded_words = [
            str(self.embs_model.embed_query(word)) for word in words_inside_brackets
        ]
        return "', '".join(embedded_words)

    def get_query(self, output):
        '''Extract and process the SQL query from the output'''
        # extract SQL query part
        match = re.search(r'SQLQuery: (.+)', output)
        if not match:
            raise ValueError("SQL query not found in the output")

        sql_query = match.group(1)
        # replace brackets in query with schema info, if needed
        processed_query = re.sub(r"\[([\w\s,]+)\]", self.replace_brackets, sql_query)
        return processed_query
    
    def get_query_gen_chain(self, query):
        '''Get query generation chain for generating SQL query from user query'''
        # create query gen prompt
        query_gen_prompt = ChatPromptTemplate.from_messages(
            [("system", postgresql_template), ("human", "{query}")]
        )
        
        # create query gen chain
        query_gen_chain = (
            RunnablePassthrough.assign(schema=self.get_schema)
            | query_gen_prompt
            | self.llm
            | StrOutputParser()
        )
        
        return query_gen_chain
    
    def gen_query(self, query: str):
        '''Generate SQL query from user query to fetch info from db'''
        # get query gen chain
        query_gen_chain = self.get_query_gen_chain(query)
        
        # invoke chain to generate output
        output = query_gen_chain.invoke({"query": query})
        
        # parse SQL query from output
        sql_query = self.get_query(output)
        
        return sql_query
    
    def gen_response(self, query: str):
        '''Generate response from user query by generating & running a SQL query on the db and performing RAG on the results'''
        # generate SQL query
        sql_query = self.gen_query(query)
        
        # Create a lambda function to return the SQL query as a dictionary
        sql_query_lambda = RunnableLambda(lambda _: {"sql_query": sql_query})

        # create response gen prompt
        rag_prompt = ChatPromptTemplate.from_messages(
            [("system", sql_rag_template), ("human", "{query}")]
        )
        
        # create rag response gen chain
        rag_chain = (
            RunnablePassthrough.assign(query=sql_query_lambda)
            | RunnablePassthrough.assign(
                schema=self.get_schema,
                response=RunnableLambda(lambda x: self.db.run((x["query"]["sql_query"]))),
            )
            | rag_prompt
            | self.llm
        )

        # invoke chain to generate output
        response = rag_chain.invoke({"query": query})

        return sql_query, response.content