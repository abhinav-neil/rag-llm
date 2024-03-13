# RAG-LLM

This repository contains code for implementing retrieval-augmented generation (RAG) with LLM agents with tools . We perform RAG using 2 kinds of databases: a tabular RDBMS (Postgres) and a graph database (Neo4j). We use OpenAI's GPT-3.5 & GPT-4 LLMs, and Langchain & OpenAI tools for interacting with the LLM agents.

## Setup
To create the environment, run the following command:
```bash
conda create -n rag-llm python=3.11
```
To activate the environment, run the following command:
```bash
conda activate rag-llm
```

Install the required packages using the following command:
```bash
poetry install
```

Save the configuration of your postgres and neo4j databases in the `.env` file in the root directory of the project. The `OPENAI_API_KEY` should also be saved here to interact with OpenAI's LLMs.

Save other configurations in the`src/config.py` file.

## Usage
The `main.ipynb` contains example code for loading & processing the postgres & neo4j databases, and for performing RAG with LLM agents.

Save the sample queries test set in the path defined in the `src/config.py` file as `TEST_QUERIES_PATH`. It should a `.csv` file with the following columns: `id`, `query`, `difficulty`, `answer`.

To evaluate the SQL RAG framework on the sample test set, run the following command:
```bash
python src/eval_sql_rag.py
```

To evaluate the Graph RAG framework on the sample test set, run the following command:
```bash
python src/eval_graph_rag.py
```


