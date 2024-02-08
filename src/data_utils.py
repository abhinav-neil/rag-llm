from ast import literal_eval
from html2text import html2text
from langchain.sql_database import SQLDatabase
from langchain.graphs import Neo4jGraph
from langchain_openai import AzureOpenAIEmbeddings
from langchain.vectorstores import Neo4jVector
import psycopg2
import pandas as pd
from src.utils import *

class SQLDBManager():
    '''
    Class for managing SQL database.
    '''
    def __init__(self):
        pass
       
    @classmethod 
    def from_env(cls, **kwargs):
        '''
        Connect to database using environment variables.
        '''
        instance = cls()
        # get postgres env variables
        host, port, db, user, password = load_postgres_env_variables()
        
        # connect to DB
        conn_str = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
        try:
            instance.db = SQLDatabase.from_uri(conn_str, **kwargs)
            # print("connected to database")
        except Exception as e:
            print(f"connection to database failed: {e}")
        
        return instance
        
    def filter_table(self, src_table: str, req_cols_path: str, primary_key: str, overwrite=False):
        '''
        Create new table with only required fields from old table.
        Args:
            src_table (str): name of table to filter
            req_cols_path (str): path to file with required fields
            primary_key (str): name of primary key
            overwrite (bool): overwrite table if it already exists
        '''
        # read required fields from file
        with open(req_cols_path, 'r') as file:
            cols = [line.strip() for line in file.readlines()]
        cols = ', '.join(cols)
        
        data_table = f'{src_table}_filtered'

        if overwrite:
            # drop table if it already exists
            self.drop_table(data_table)

        # create new table with required fields from old table
        create_table_query = f"""
        CREATE TABLE {data_table} AS 
        SELECT {cols} FROM {src_table} WITH DATA;
        ALTER TABLE {data_table} ADD PRIMARY KEY ({primary_key});
        """
        # run query to create new table
        try:
            self.db.run(create_table_query)
            print(f"table {data_table} created successfully.")
        except Exception as e:
            print(f"an error occurred: {e}")
            
    def clean_html(self, data_table: str, cols_to_clean: list, primary_key: str):
        '''
        Clean html from columns in table.
        Args:
            data_table (str): name of table
            cols_to_clean (list): list of columns to clean
            primary_key (str): name of primary key
        '''
        for col in cols_to_clean:
            # fetch rows for the column to clean
            rows_str = self.db.run(f"SELECT {primary_key}, {col} FROM {data_table}")
            rows = literal_eval(rows_str)  # convert string to list
            rows = [(row[0], row[1]) for row in rows]  # convert list of tuples to list of (id, description)

            # clean html and escape single quotes
            cleaned_rows = [(row[0], html2text(row[1]) if row[1] else None) for row in rows]
            cleaned_rows = [(row[0], row[1].replace("'", "''") if row[1] else 'NULL') for row in cleaned_rows]

            # update the database with cleaned text
            for pk, cleaned_text in cleaned_rows:
                update_query = f"UPDATE {data_table} SET {col} = '{cleaned_text}' WHERE {primary_key} = '{pk}';"
                try:
                    self.db.run(update_query)
                except Exception as e:
                    print(f"error updating row {pk}: {e}")
                    continue
                            
    def embed_objs(self, data_table: str, cols_to_embed: list, pk: str):
        '''
        Create new column in table with embeddings.
        Args:
            data_table (str): name of table
            cols_to_embed (list): list of column names to embed
            pk (str): name of the primary key or unique identifier column
        '''
        # check and create a column for embeddings if it doesn't exist
        embs_col_name = "embeddings"
        self.db.run(f"ALTER TABLE {data_table} ADD COLUMN IF NOT EXISTS {embs_col_name} DOUBLE PRECISION[];")

        # get column values to embed and the ids
        cols_to_embed_str = ', '.join(cols_to_embed)
        result_str = self.db.run(f'SELECT {pk}, {cols_to_embed_str} FROM {data_table}')
        ids_and_values = literal_eval(result_str)
        ids = [row[0] for row in ids_and_values]
        column_values = [' '.join(map(str, row[1:])) for row in ids_and_values]

        # create embeddings
        embs_model = AzureOpenAIEmbeddings(azure_deployment="text-embedding-ada-002") # instantiate embeddings model
        embeddings = embs_model.embed_documents(column_values)

        # update table with embeddings
        for i, id in enumerate(ids):
            embedding = embeddings[i]
            query = f"UPDATE {data_table} SET {embs_col_name} = ARRAY{embedding} WHERE {pk} = '{id}';"
            try:
                self.db.run(query)
            except Exception as e:
                print(f"an error occurred: {e}")

        print(f"embeddings col {embs_col_name} created successfully.")
              
    def drop_cols(self, table_name: str, cols_to_drop: list):
        '''
        Drop columns from table.
        Args:
            table_name (str): name of table
            cols_to_drop (list): list of column names to drop
        '''
        for col in cols_to_drop:
            # drop column
            drop_col_query = f"ALTER TABLE {table_name} DROP COLUMN {col};"
            try:
                self.db.run(drop_col_query)
            except Exception as e:
                print(f"an error occurred while dropping column {col}: {e}")
        print('done.')
        
    def drop_table(self, table_name: str):
        '''
        Drop table.
        Args:
            table_name (str): name of table
        '''
        # drop table
        drop_table_query = f"""
        DROP TABLE {table_name};
        """
        try:
            self.db.run(drop_table_query)
            print(f"table {table_name} dropped successfully.")
        except Exception as e:
            print(f"an error occurred: {e}")

    def get_col_names(self, schema: str, table: str) -> list:
        '''
        Get column names from table.
        '''
        select_cols_q = f'''
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = '{schema}'
            AND table_name = '{table}';
        '''
        cols = self.db.run(select_cols_q)
        cols = literal_eval(cols)
        cols = [col[0] for col in cols]
        
        return cols

def parse_db_output(output_str: str):    
    
    '''
    Parse output from SQL database from string to list of tuples.
    Args:
        output_str (str): output from SQL database
    Returns:
        parsed_data (list): list of tuples
    '''
    # function to convert string to appropriate type
    def convert_element(e):
        try:
            return literal_eval(e)
        except (ValueError, SyntaxError):
            return e.strip("'")

    # split the string into individual tuples
    tuples = output_str.strip('[]').split('), (')
    parsed_data = []

    for t in tuples:
        t = t.strip('()')
        elements = []
        temp_element = ''
        in_datetime = False
        for char in t:
            if char == ',' and not in_datetime:
                elements.append(temp_element)
                temp_element = ''
            else:
                temp_element += char
                if char == '(':
                    in_datetime = True
                elif char == ')':
                    in_datetime = False
        elements.append(temp_element) 

        # convert elements to their appropriate types
        converted_elements = [convert_element(e.strip()) for e in elements]
        parsed_data.append(tuple(converted_elements))

    return parsed_data

class Neo4jGraphManager():
    '''
    Class for managing Neo4j graph database.
    '''
    def __init__(self):
        pass
    
    @classmethod
    def from_env(cls):
        '''
        Connect to database using environment variables.
        '''
        instance = cls()
        instance.graph = Neo4jGraph()
        return instance
    
    def from_table(self, table: str, reset=True):
        '''
        Create a neo4j graph from a table (in string format)
        Args:
            table (str): name of table
            reset (bool): reset graph if it already exists
        '''
        # table_data = parse_db_output(table) # convert string to list of tuples
        # connect to postgres db
        host, port, db, user, password = load_postgres_env_variables()
        conn = psycopg2.connect(f"host={host} port={port} dbname={db} user={user} password={password}")
        
        # fetch data from table
        query = f"SELECT * FROM {table};"
        df = pd.read_sql(query, conn)
        conn.close()                        
        
        if reset:
            # clear graph (in case it already exists)
            self.graph.query('MATCH (n) DETACH DELETE n')

        # iter over df rows
        for _, row in df.iterrows():
            # convert tuple to dict
            # row_dict = {cols[i]: row[i] for i in range(len(cols))}
            row_dict = row.to_dict()
            obj_class = row_dict.get('pxobjclass', 'Object')
            # create a node for each row with dynamic properties
            self.graph.query(f"CREATE (n:{obj_class}) SET n += $props", {"props": row_dict})
               
        # create relationships
        # user stories belonging to epics
        self.graph.query(
            """
            MATCH (us:UserStory), (epic:Epic) WHERE us.epicid = epic.pyid
            MERGE (us)-[:IS_STORY_OF_EPIC]->(epic)
            """
        )
        # epics belonging to goals
        self.graph.query(
            """
            MATCH (epic:Epic), (goal:Goal) WHERE epic.goalid = goal.pyid
            MERGE (epic)-[:IS_EPIC_OF_GOAL]->(goal)
            """
        )
        # goals belonging to projects
        # Note: Adjust the label for projects if you have a specific one
        self.graph.query(
            """
            MATCH (goal:Goal), (project:Project) WHERE goal.projectid = project.pyid
            MERGE (goal)-[:IS_GOAL_OF_PROJECT]->(project)
            """
        )
        
    def embed_objs(
        self,
        obj_types: list = ['Epic', 'UserStory', 'Goal', 'Project', 'Backlog'],
        text_cols: list = ['pylabel', 'description']):
        '''
        Get embeddings from text descriptions of objects in graph.
        Args:
        - obj_types (list): list of object types
        - text_cols (list): list of text columns to embed
        '''
        embs_model = AzureOpenAIEmbeddings(azure_deployment="text-embedding-ada-002") # instantiate embeddings model
        
        url, username, password, db = load_neo4j_env_variables()    # load neo4j env vars
        
        # create vector index & embs for each object type
        for obj in obj_types:
            vector_index = Neo4jVector.from_existing_graph(
                embs_model,
                url=url,
                username=username,
                password=password,
                index_name=obj,
                node_label=obj,
                text_node_properties=text_cols,
                embedding_node_property='embedding',
            )