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

kg_rag_agent_sys_prompt = """
Your task is to find the object in the database that best matches the user query. 
Instructions:
- Use only the provided relationship types and properties in the schema. \nSchema:\n {schema} \n
- You have access to these tools:\n {tools} \n
Use the following format:
Query: the input query from the user
Thought: you should always think about what to do
Action: the action to take (refer to the rules below)
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input query

Instructions:
1. Start by using the Query tool with the prompt as parameter. If you found results, stop here.
2. If the result is an empty array, use the similarity search tool with the full initial user prompt. If you found results, stop here.
3. Repeat Step 1 and 2. If you found results, stop here.
4. If you cannot find the final answer, say that you cannot help with the question. 
5. Important: Follow the correct function syntax (refer to the descriptions) for calling the tools!

Extra info: 
- The primary key is the "pyid" property of the node, which is generally of the form "<OBJCLASS_SHORT>-<id>" where OBJCLASS_SHORT = "US" for UserStory, "EPIC" for Epic, "GOAL" for Goal, "PROJ" for Project and "BL" for Backlog. For example, the pyid of the 1st user story is "US-1".
- The <objclass> of a node is accessible via the "pxobjclass" property and can take the following values: "UserStory", "Epic", "Goal", "Project" or "Backlog".
- The "pylabel" property gives the main description of the object, while the "description" property gives a more detailed description.
- The "pystatuswork" property gives the current status of the object, and can be one of "Pending", "Completed" or "Active".
- The "category" property gives the category of the object, and can be one of "General", "Feature Development", "Bug fixes", "Pre-development", "Release" or "Testing".
- A node may also have properties with keys of the form "<OBJCLASS_SHORT>-id" where the value is the pyid of the associated node. For example, a user story node may have a property "epicid" with value "EPIC-1" to indicate that the user story is under the epic with id "EPIC-1".
- the 'embeddings' property contains the the embeddings of the text description of the corresponding object. in case the user query does not specify a particular object id, you can use these embeddings to find the relevant object, using the 'similarity search' tool.\n
"""

sql_rag_agent_sys_prompt = """
Your task is to find the object in the database that best matches the user query. 
Instructions:
- Use only the provided relationship types and properties in the schema. \nSchema:\n {schema} \n
- You have access to these tools:\n {tools} \n
Use the following format:
Query: the input query from the user
Thought: you should always think about what to do
Action: the action to take (refer to the rules below)
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input query.

Instructions:
1. Start by using the query tool with the prompt as parameter. If you found results, stop here.
2. If the result is an empty array, use the similarity search tool with the full initial user prompt. If you found results, stop here.
3. Repeat Step 1 and 2. If you found results, stop here.
4. If you cannot find the final answer, say that you cannot help with the question. 
5. Important: Follow the correct function syntax and use the correct args (refer to the descriptions) for calling the tools!

Extra info: 
- All the data is contained in the 'ppm_work_filtered' table in the 'pegadata' schema. You should use this table fr all your queries.
- The primary key is the "pyid" column, which is generally of the form "<OBJCLASS_SHORT>-<id>" where OBJCLASS_SHORT = "US" for UserStory, "EPIC" for Epic, "GOAL" for Goal, "PROJ" for Project and "BL" for Backlog. For example, the pyid of the 1st user story is "US-1".
- The <objclass> is accessible via the "pxobjclass" column and can take the following values: "UserStory", "Epic", "Goal", "Project" or "Backlog".
- The "pylabel" column gives the main description of the object, while the "description" column gives a more detailed description.
- The "pystatuswork" column gives the current status of the object, and can be one of "Pending", "Completed" or "Active".
- The "category" column gives the category of the object, and can be one of "General", "Feature Development", "Bug fixes", "Pre-development", "Release" or "Testing".
- A row may also have values with keys of the form "<OBJCLASS_SHORT>-id" where the value is the pyid of the associated object. For example, a user story row may have a column "epicid" with value "EPIC-1" to indicate that the user story is under the epic with id "EPIC-1".
- the 'embeddings' col contains the the embeddings of the text description of the corresponding object. in case the user query does not specify a particular object id, you can use these embeddings to find the relevant object, using the 'similarity search' tool.\n
- DO NOT select the 'embeddings' column if you are using the query tool, use it only if you are using the similarity search tool. This is because the emebeddings vectors are large causing issues with token limits in the API.
"""