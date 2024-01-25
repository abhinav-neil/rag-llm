sql_rag_prompt = """Given an input question, first create a syntactically correct query to run, then look at the results of the query and return the answer.
Use the following format:
Question: Question
SQLQuery: SQL Query to run
SQLResult: Result of the SQLQuery
Answer: Final answer
Only use the following tables:\n {table_info}.
Question: {input}"""

kg_rag_prompt = """Task: Generate Cypher statement to query a graph database. 
Instructions:\n Use only the provided relationship types and properties in the schema. \nSchema:\n{schema}\n
Extra info: 
- The primary key is the "pyid" property of the node, which is generally of the form "<OBJCLASS_SHORT>-<id>" where OBJCLASS_SHORT = "US" for UserStory, "EPIC" for Epic, "GOAL" for Goal, "PROJ" for Project and "BL" for Backlog. For example, the pyid of the 1st user story is "US-1".
- The <objclass> of a node is accessible via the "pxobjclass" property and can take the following values: "UserStory", "Epic", "Goal", "Project" or "Backlog".
- The "pylabel" property gives the main description of the object, while the "description" property gives a more detailed description.
- The "pystatuswork" property gives the current status of the object, and can be one of "Pending", "Completed" or "Active".
- The "category" property gives the category of the object, and can be one of "General", "Feature Development", "Bug fixes", "Pre-development", "Release" or "Testing".
- A node may also have properties with keys of the form "<OBJCLASS_SHORT>-id" where the value is the pyid of the associated node. For example, a user story node may have a property "epicid" with value "EPIC-1" to indicate that the user story is under the epic with id "EPIC-1".
Other instructions:
- Do not include any text except the generated Cypher statement.
- If your're not sure about the exact case of a property value, convert to lowercase before matching within the query.
The question is: {question}"""