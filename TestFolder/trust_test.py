from fastapi import FastAPI, Query, HTTPException
from pathlib import Path
import sys
import boto3
import subprocess
import uvicorn
import logging
import requests
import time
import random

parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

REGION = "us-east-1"

# Create FastAPI app
app = FastAPI()

@app.get("/test")
def root():
    return {"message": "Hello from cluster 1"}