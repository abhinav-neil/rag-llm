from pathlib import Path
from typing import List
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import TextLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.graphs import Neo4jGraph
from langchain.text_splitter import TokenTextSplitter
from neo4j.exceptions import ClientError

txt_path = Path(__file__).parent / "dune.txt"

graph = Neo4jGraph()

# Embeddings & LLM models
embeddings = OpenAIEmbeddings()
embedding_dimension = 1536
llm = ChatOpenAI(temperature=0)

# Load the text file
print(f"attempting to load file from: {txt_path}")
loader = TextLoader(str(txt_path), autodetect_encoding=True)
documents = loader.load()

# Ingest Parent-Child node pairs
parent_splitter = TokenTextSplitter(chunk_size=512, chunk_overlap=24)
child_splitter = TokenTextSplitter(chunk_size=100, chunk_overlap=24)
parent_documents = parent_splitter.split_documents(documents)

for i, parent in enumerate(parent_documents):
    child_documents = child_splitter.split_documents([parent])
    params = {
        "parent_text": parent.page_content,
        "parent_id": i,
        "parent_embedding": embeddings.embed_query(parent.page_content),
        "children": [
            {
                "text": c.page_content,
                "id": f"{i}-{ic}",
                "embedding": embeddings.embed_query(c.page_content),
            }
            for ic, c in enumerate(child_documents)
        ],
    }
    # Ingest data
    graph.query(
        """
    MERGE (p:Parent {id: $parent_id})
    SET p.text = $parent_text
    WITH p
    CALL db.create.setVectorProperty(p, 'embedding', $parent_embedding)
    YIELD node
    WITH p 
    UNWIND $children AS child
    MERGE (c:Child {id: child.id})
    SET c.text = child.text
    MERGE (c)<-[:HAS_CHILD]-(p)
    WITH c, child
    CALL db.create.setVectorProperty(c, 'embedding', child.embedding)
    YIELD node
    RETURN count(*)
    """,
        params,
    )
    # Create vector index for child
    try:
        graph.query(
            "CALL db.index.vector.createNodeIndex('parent_document', "
            "'Child', 'embedding', $dimension, 'cosine')",
            {"dimension": embedding_dimension},
        )
    except ClientError:  # already exists
        pass
    # Create vector index for parents
    try:
        graph.query(
            "CALL db.index.vector.createNodeIndex('typical_rag', "
            "'Parent', 'embedding', $dimension, 'cosine')",
            {"dimension": embedding_dimension},
        )
    except ClientError:  # already exists
        pass