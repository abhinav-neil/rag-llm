# Postgres DB
TABLE_SCHEMA = "public"
TABLE_NAME = "data"
TABLE_PRIMARY_KEY = "id"
REQ_COLS_PATH = "data/req_cols.txt"
TEXT_COL = "description"
COLS_TO_EMBED = ["label", "description"]

# Graph DB
GRAPH_OBJ_TYPES = ["UserStory", "Epic", "Goal", "Project"]
# OpenAI
OPENAI_LLM_VERSION = "gpt-4"
MAX_TOKENS = 100
TEMPERATURE = 0.0

# Eval
TEST_QUERIES_PATH = "data/sample_queries.csv"
SQL_RESPONSES_EVAL_PATH = "outputs/sql-rag/responses.csv"
SQL_RESULTS_PATH = "outputs/sql-rag/results.json"
GRAPH_RESPONSES_EVAL_PATH = "outputs/kg-rag/responses.csv"
GRAPH_RESULTS_PATH = "outputs/kg-rag/results.json"
