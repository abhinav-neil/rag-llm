import os
import re
import json 
from typing import Optional
from langchain.chat_models import AzureChatOpenAI
from langchain.embeddings import AzureOpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain.sql_database import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from sql_pgvector.prompt_templates import final_template, postgresql_template
from src.data_utils import SQLDBManager

# connect to SQL db
dbm = SQLDBManager.from_env()

# load schema config
with open("src/db_config.json", "r") as f:
    db_config = json.load(f)

# note: the data_table should have a col w embeddings. run dbm.create_embs_col() to create it, before running this script


# Choose LLM and embeddings model
llm = AzureChatOpenAI(model='gpt-4-32k', max_tokens=500, temperature=0.9, stop=["\nSQLResult:"])

# -----------------
# Define functions
# -----------------
def get_schema(_):
    return db.get_table_info()


def run_query(query):
    return db.run(query)


def replace_brackets(match):
    words_inside_brackets = match.group(1).split(", ")
    embedded_words = [
        str(embs_model.embed_query(word)) for word in words_inside_brackets
    ]
    return "', '".join(embedded_words)


def get_query(query):
    sql_query = re.sub(r"\[([\w\s,]+)\]", replace_brackets, query)
    return sql_query


# -----------------------
# Now we create the chain
# -----------------------

query_generation_prompt = ChatPromptTemplate.from_messages(
    [("system", postgresql_template), ("human", "{question}")]
)

sql_query_chain = (
    RunnablePassthrough.assign(schema=dbm.get_table_info([db_config['data_table']]))
    | query_generation_prompt
    | llm.bind(stop=["\nSQLResult:"])
    | StrOutputParser()
)


final_prompt = ChatPromptTemplate.from_messages(
    [("system", final_template), ("human", "{question}")]
)

full_chain = (
    RunnablePassthrough.assign(query=sql_query_chain)
    | RunnablePassthrough.assign(
        schema=get_schema,
        response=RunnableLambda(lambda x: db.run(get_query(x["query"]))),
    )
    | final_prompt
    | llm
)


class InputType(BaseModel):
    question: str


chain = full_chain.with_types(input_type=InputType)
