from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import subprocess
import uvicorn
import logging
import requests
import time

# Create FastAPI app
app = FastAPI()

class WriteRequest(BaseModel):
    query: str

@app.post("/write")
def receive_request(write_request: WriteRequest):

    query = write_request.query

    result = execute_query(query)
    # if "error" in result:
    #     raise HTTPException(status_code=500, detail=result["error"])
    return result

    #TODO: Allow a replication of the operation to the workers



@app.get("/read")
def read_db(
    query: str = Query(..., description="SQL query to execute")
):
    result = execute_query(query)
    # if "error" in result:
        # raise HTTPException(status_code=500, detail=result["error"])
    return result


def execute_query(query):
    try:
        # Executa o comando MySQL diretamente no terminal
        result = subprocess.run(
            ['sudo', 'mysql', '-e', query],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            print(f"Resultado: {result}")
        else:
            print(f"Erro: {result.stderr}")
            raise Exception({result.stderr})
        print("Ola")
        return {"result": result, "status": "success"}   
    except Exception as e:
        return {"error": f"Erro ao executar a query: {e}", "status": "failed"}