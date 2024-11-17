from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
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

    #TODO: Uptade the database and verify if the operation was a success

    result = "success"

    #TODO: Allow a replication of the operation to the workers
    if result == "success":
        return {"message": "success"}
    else:
        return {"message": "Fail"}
    


@app.get("/read")
def receive_request(
    query: str = Query(..., description="SQL query to execute")
):
    #TODO Change the database and return the response

    return {"message": "This is a read request"}