from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from langserve import add_routes
from rag_neo4j import chain as neo4j_chain
import uvicorn

app = FastAPI()


@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")


add_routes(app, neo4j_chain, path="/rag-neo4j")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
