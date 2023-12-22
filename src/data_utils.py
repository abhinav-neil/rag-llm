from typing import Optional
import ast
from html2text import html2text
from langchain.sql_database import SQLDatabase
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
        
    def filter_table(self, src_table: str, cols_path: str, primary_key: str):
        '''
        Create new table with only required fields from old table.
        Args:
            src_table (str): name of table to filter
            cols_path (str): path to file with required fields
            primary_key (str): name of primary key
        
        '''
        # read required fields from file
        with open(cols_path, 'r') as file:
            columns = [line.strip() for line in file.readlines()]
        columns_str = ', '.join(columns)

        # create new table with required fields from old table
        # create table query
        data_table = f'{src_table}_filtered'
        
        create_table_query = f"""
        CREATE TABLE {data_table} AS 
        SELECT {columns_str} 
        FROM {src_table}
        WITH DATA;
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
            rows = ast.literal_eval(rows_str)  # convert string to list
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
                            
    def create_embs_col(self, data_table: str, col_to_embed: str, embs_model):
        '''
        Create new column in table for storing embeddings.
        Args:
            data_table (str): name of table
            col_to_embed (str): name of column to embed
            embs_model: embeddings model
        '''
        # check and create a column for embeddings if it doesn't exist
        embs_col_name = f"{col_to_embed}_embs"
        self.db.run(f"ALTER TABLE {data_table} ADD COLUMN IF NOT EXISTS {embs_col_name} DOUBLE PRECISION[];")

        # get column values to embed
        result_str = self.db.run(f'SELECT {col_to_embed} FROM {data_table}')
        column_values = [s[0] for s in ast.literal_eval(result_str)]
        embeddings = embs_model.embed_documents(column_values)

        # update table with embeddings
        for i, value in enumerate(column_values):
            cleaned_value = value.replace("'", "''")  # escape single quotes
            embedding = embeddings[i]
            query = f"UPDATE {data_table} SET {embs_col_name} = ARRAY{embedding} WHERE {col_to_embed} = '{cleaned_value}';"
            try:
                self.db.run(query)
            except Exception as e:
                print(f"An error occurred: {e}")

        print(f"embeddings col {embs_col_name} created successfully.")
       
    # def ingest_data(self, data_table: str, text_col: str, primary_key: str, embs_model, filter_table: bool=True, req_cols_path: Optional[str] = None, clean_html: bool=True):
    #     """
    #     Ingests data from a SQL database into a new table, with a new column containing the embeddings of the text column.
    #     """
    #     # filter data table to only include required columns and create new table (if it doesn't exist)
    #     if filter_table:
    #         assert req_cols_path is not None and os.path.exists(req_cols_path), "please provide a valid path to a file with required columns."
    #         new_data_table = f"{data_table}_filtered"
    #         self.filter_table(data_table, req_cols_path, new_data_table, primary_key)
        
    #     # clean html text in text col before creating embeddings
    #     if clean_html:
    #         new_data_table = f"{data_table}_filtered" if filter_table else data_table
    #         self.clean_html(new_data_table, [text_col], primary_key)
        
    #     # create embeddings for text col
    #     self.create_embs_col(new_data_table, text_col, embs_model)
        
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