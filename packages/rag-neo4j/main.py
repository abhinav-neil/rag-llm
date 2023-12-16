from rag_neo4j.chain import chain

if __name__ == "__main__":
    original_query = "What is the plot of the Dune?"
    print(
        chain.invoke(
            {"question": original_query},
            {"configurable": {"strategy": "parent_document"}},
        )
    )
