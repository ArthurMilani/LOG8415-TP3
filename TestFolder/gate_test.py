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

def test():
    try:
        result = requests.get("http://172.31.81.196:8000/test")
        print(result.json())
    except requests.RequestException as e:
        print(f"Error sending request to localhost: {e}")
        return None


test()