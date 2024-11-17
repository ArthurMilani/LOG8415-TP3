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

    #TODO: Uptade the database
    return {"message": "This is a write request"}


@app.get("/read")
def read_db(
    query: str = Query(..., description="SQL query to execute")
):
    #TODO Change the database and return the response

    return {"message": "This is a read request"}