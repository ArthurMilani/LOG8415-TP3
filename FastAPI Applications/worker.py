from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import subprocess
import uvicorn

# Create FastAPI app
app = FastAPI()

class WriteRequest(BaseModel):
    query: str


#Only write requests
@app.post("/write")
def receive_request(write_request: WriteRequest):

    query = write_request.query
    query = "USE sakila;" + query + ";" #Building the query to be executed
    result = execute_query(query)
    if result["status"] == "failed":
        raise HTTPException(status_code=400, detail=result["error"])
    return result


#Only read requests
@app.get("/read")
def read_db(
    query: str = Query(..., description="SQL query to execute")
):
    query = "USE sakila;" + query + ";" #Building the query to be executed
    result = execute_query(query)
    if result["status"] == "failed":
        raise HTTPException(status_code=400, detail=result["error"])
    return result


#Function to execute the query in the database
def execute_query(query):
    try:
        #The command will be executed in the terminal
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
        return {"result": result, "status": "success"}   
    except Exception as e:
        print(f"Query execution error in one worker: {e}")
        return {"error": f"Query execution error in one worker: {e}", "status": "failed"}