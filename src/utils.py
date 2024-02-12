import os
import re
import json
from typing import Literal
from dotenv import load_dotenv
import pandas as pd

def get_env_variable(var_name):
    load_dotenv()
    value = os.environ.get(var_name)
    if value is None:
        raise EnvironmentError(f"Environment variable {var_name} not set.")
    return value

def load_postgres_env_variables():
    '''
    Load environment variables for postgres database.
    '''
    host = get_env_variable("POSTGRES_HOST")
    port = get_env_variable("POSTGRES_PORT")
    db = get_env_variable("POSTGRES_DB")
    user = get_env_variable("POSTGRES_USER")
    password = get_env_variable("POSTGRES_PASSWORD")
    
    return host, port, db, user, password

def load_neo4j_env_variables():
    '''
    Load environment variables for neo4j database.
    '''
    uri = get_env_variable("NEO4J_URI")
    user = get_env_variable("NEO4J_USERNAME")
    password = get_env_variable("NEO4J_PASSWORD")
    db = os.environ.get("NEO4J_DB", "neo4j")
    
    return uri, user, password, db

def setup_azure_openai(
    api_base: str = "https://aze-openai-03.openai.azure.com/",
    api_version: Literal[
        "2022-12-01",
        "2023-03-15-preview",
        "2023-05-15",
        "2023-06-01-preview",
        "2023-07-01-preview",
        "2023-09-15-preview",
        "2023-10-01-preview",
        "2023-12-01-preview"
    ] = "2023-07-01-preview",
):
    """Convenience function to automagically setup Azure AD-based authentication
    for the Azure OpenAI service. Mostly meant as an internal tool within Pega,
    but can of course also be used beyond.

    Prerequisites (you should only need to do this once!):
    - Download Azure CLI (https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
    - Once installed, run 'az login' in your terminal
    - Additional dependencies: `(pip install)` azure-identity and `(pip install)` openai

    Running this function automatically sets, among others:
    - `openai.api_key`
    - `os.environ["OPENAI_API_KEY"]`

    This should ensure that you don't need to pass tokens and/or api_keys around.
    The key that's set has a lifetime, typically of one hour. Therefore, if you
    get an error message like 'invalid token', you may need to run this method again
    to refresh the token for another hour.

    Parameters
    ----------
    api_base : str
        The url of the Azure service name you'd like to connect to
        If you have access to the Azure OpenAI playground
        (https://oai.azure.com/portal), you can easily find this url by clicking
        'view code' in one of the playgrounds. If you have access to the Azure portal
        directly (https://portal.azure.com), this will be found under 'endpoint'.
        Else, ask your system administrator for the correct url.
    api_version : str
        The version of the api to use
    """
    try:
        from azure.identity import (
            AzureCliCredential,
            ChainedTokenCredential,
            ManagedIdentityCredential,
            EnvironmentCredential,
        )
    except ImportError:
        raise ImportError(
            "Can't find azure identity. Install through `pip install azure-identity`."
        )
    try:
        import openai
    except ImportError:
        raise ImportError(
            "Can't find openai. Install through `pip install --upgrade openai."
        )
    import os

    # Define strategy which potential authentication methods should be tried to gain an access token
    credential = ChainedTokenCredential(
        ManagedIdentityCredential(), EnvironmentCredential(), AzureCliCredential()
    )
    try:
        access_token = credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        )
    except Exception as e:
        raise Exception(
            f"Exception: {e}. \nAre you sure you've installed Azure CLI & ran `az login`?"
        )

    if int(openai.version.VERSION.split(".")[0]) < 1:
        os.environ["OPENAI_API_KEY"] = openai.api_key = access_token.token
        os.environ["OPENAI_API_BASE"] = openai.api_base = api_base
        os.environ["OPENAI_API_VERSION"] = openai.api_version = api_version
        os.environ["OPENAI_API_TYPE"] = "azure_ad"

    else:
        os.environ["AZURE_OPENAI_AD_TOKEN"] = access_token.token
        os.environ["AZURE_OPENAI_ENDPOINT"] = api_base
        os.environ["OPENAI_API_VERSION"] = api_version
        
    print("Successfully setup Azure OpenAI authentication")
    
    
def eval_rag_responses(responses_eval_path: str, results_path: str) -> dict:
    """
    Evaluate RAG responses and return metrics dict.
    Args:
        responses_eval_path: Path to the responses_eval.csv file.
        results_path: Path to save the results.
    Returns:
        metrics: Dict with metrics.
    """
    df_responses_eval = pd.read_csv(responses_eval_path, sep=';', index_col='id')
    num_queries_easy = len(df_responses_eval[df_responses_eval['difficulty'] == 'easy'])
    num_queries_hard = len(df_responses_eval[df_responses_eval['difficulty'] == 'hard'])
    num_queries = len(df_responses_eval)
    num_correct_easy = len(df_responses_eval[(df_responses_eval['difficulty'] == 'easy') & (df_responses_eval['correct'] == True)])
    num_correct_hard = len(df_responses_eval[(df_responses_eval['difficulty'] == 'hard') & (df_responses_eval['correct'] == True)])
    num_correct = len(df_responses_eval[df_responses_eval['correct'] == True])
    
    eval_res = {
        'num_queries': num_queries,
        'num_correct': num_correct,
        'num_queries_easy': num_queries_easy,
        'num_correct_easy': num_correct_easy,
        'num_queries_hard': num_queries_hard,
        'num_correct_hard': num_correct_hard,
        'accuracy': num_correct / num_queries,
        'accuracy_easy': num_correct_easy / num_queries_easy,
        'accuracy_hard': num_correct_hard / num_queries_hard,
    }
    
    with open(results_path, 'w') as f:
        json.dump(eval_res, f)
    
    return eval_res