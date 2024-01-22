rag_sql_prompt = """Given an input question, first create a syntactically correct query to run, then look at the results of the query and return the answer.
Use the following format:
Question: Question
SQLQuery: SQL Query to run
SQLResult: Result of the SQLQuery
Answer: Final answer
Only use the following tables:\n {table_info}.
Question: {input}"""

kg_rag_prompt = """Task: Generate Cypher statement to query a graph database. 
Instructions:\n Use only the provided relationship types and properties in the schema. \nSchema:\n{schema}\n
Extra info: The primary key is the "pyid" property of the node, which is generally of the form "<objclass>-<id>", where <objclass> = "UserStory", "Epic", "Goal", "Project" or "Backlog". The <objclass> of a node is accessible via the "pxobjclass" property. A node may also have properties with keys of the form "<objclass>id" where the value is the pyid of the associated node. For example, a user story node may have a property "epicid" with value "EPIC-1" to indicate that the user story is under the epic with id "EPIC-1".
Do not include any text except the generated Cypher statement.
The question is: {question}"""