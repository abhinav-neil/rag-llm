from langchain.sql_database import SQLDatabase
import ast
from html2text import html2text
from src.utils import *

class SQLDBManager():
    '''
    Class for managing SQL database.
    '''
    def __init__(self):
        pass
       
    @classmethod 
    def from_env(cls):
        '''
        Connect to database using environment variables.
        '''
        instance = cls()
        # get postgres env variables
        postgres_user = get_env_variable("POSTGRES_USER")
        postgres_password = get_env_variable("POSTGRES_PASSWORD")
        postgres_db = get_env_variable("POSTGRES_DB")
        postgres_host = get_env_variable("POSTGRES_HOST")
        postgres_port = get_env_variable("POSTGRES_PORT")
        
        # connect to DB
        instance.connect_to_db(postgres_user, postgres_password, postgres_db, postgres_host, postgres_port)
        
        return instance
        
    def connect_to_db(self, postgres_user: str, postgres_password: str, postgres_db: str, postgres_host: str, postgres_port: str):
        # connect to DB
        connection_string = (
            f"postgresql+psycopg2://{postgres_user}:{postgres_password}"
            f"@{postgres_host}:{postgres_port}/{postgres_db}"
        )
        try:
            self.db = SQLDatabase.from_uri(connection_string)
            print("connected to database successfully.")
        except Exception as e:
            print(f"connection to database failed: {e}")
        
    def filter_table(self, table_name: str, cols_path: str, new_table_name: str, primary_key: str):
        '''
        Create new table with only required fields from old table.
        Args:
            table_name (str): name of table to filter
            cols_path (str): path to file with required fields
            new_table_name (str): name of new table
            primary_key (str): name of primary key
        
        '''
        # read required fields from file
        with open(cols_path, 'r') as file:
            columns = [line.strip() for line in file.readlines()]
        columns_str = ', '.join(columns)

        # create new table with required fields from old table
        # create table query
        create_table_query = f"""
        CREATE TABLE {new_table_name} AS 
        SELECT {columns_str} 
        FROM {table_name}
        WITH DATA;
        ALTER TABLE {new_table_name} ADD PRIMARY KEY ({primary_key});
        """
        # run query to create new table
        try:
            self.db.run(create_table_query)
            print(f"table {new_table_name} created successfully.")
        except Exception as e:
            print(f"an error occurred: {e}")
            
    def clean_html(self, table_name: str, cols_to_clean: list, primary_key: str):
        '''
        Clean html from columns in table.
        Args:
            table_name (str): name of table
            cols_to_clean (list): list of columns to clean
            primary_key (str): name of primary key
        '''
        for col in cols_to_clean:
            # fetch rows for the column to clean
            rows_str = self.db.run(f"SELECT {primary_key}, {col} FROM {table_name}")
            rows = ast.literal_eval(rows_str)  # convert string to list
            rows = [(row[0], row[1]) for row in rows]  # convert list of tuples to list of (id, description)

            # clean html and escape single quotes
            cleaned_rows = [(row[0], html2text(row[1]) if row[1] else None) for row in rows]
            cleaned_rows = [(row[0], row[1].replace("'", "''") if row[1] else 'NULL') for row in cleaned_rows]

            # update the database with cleaned text
            for pk, cleaned_text in cleaned_rows:
                update_query = f"UPDATE {table_name} SET {col} = '{cleaned_text}' WHERE {primary_key} = '{pk}';"
                try:
                    self.db.run(update_query)
                except Exception as e:
                    print(f"error updating row {pk}: {e}")
                    continue
                            
    def create_embs_col(self, table_name: str, col_to_embed: str, embs_model):
        '''
        Create new column in table for storing embeddings.
        Args:
            table_name (str): name of table
            col_to_embed (str): name of column to embed
            embs_model (EmbeddingsModel): embeddings model
        '''
        # check and create a column for embeddings if it doesn't exist
        embs_col_name = f"{col_to_embed}_embs"
        self.db.run(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {embs_col_name} DOUBLE PRECISION[];")

        # get column values to embed
        result_str = self.db.run(f'SELECT {col_to_embed} FROM {table_name}')
        column_values = [s[0] for s in ast.literal_eval(result_str)]
        embeddings = embs_model.embed_documents(column_values)

        # update table with embeddings
        for i, value in enumerate(column_values):
            cleaned_value = value.replace("'", "''")  # escape single quotes
            embedding = embeddings[i]
            query = f"UPDATE {table_name} SET {embs_col_name} = ARRAY{embedding} WHERE {col_to_embed} = '{cleaned_value}';"
            try:
                self.db.run(query)
            except Exception as e:
                print(f"An error occurred: {e}")

        print(f"embeddings col {embs_col_name} created successfully.")
        
    def drop_col(self, table_name: str, col_to_drop: str):
        '''
        Drop column from table.
        Args:
            table_name (str): name of table
            col_to_drop (str): name of column to drop
        '''
        # drop column
        drop_col_query = f"""
        ALTER TABLE {table_name} DROP COLUMN {col_to_drop};
        """
        try:
            self.db.run(drop_col_query)
            print(f"column {col_to_drop} dropped successfully.")
        except Exception as e:
            print(f"an error occurred: {e}")
            
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
