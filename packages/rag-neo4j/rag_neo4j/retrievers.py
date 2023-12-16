from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Neo4jVector

# Typical RAG retriever

typical_rag = Neo4jVector.from_existing_index(
    OpenAIEmbeddings(), index_name="typical_rag"
)

# Parent retriever

parent_query = """
MATCH (node)<-[:HAS_CHILD]-(parent)
WITH parent, max(score) AS score // deduplicate parents
RETURN parent.text AS text, score, {} AS metadata LIMIT 1
"""

parent_vectorstore = Neo4jVector.from_existing_index(
    OpenAIEmbeddings(),
    index_name="parent_document",
    retrieval_query=parent_query,
)
