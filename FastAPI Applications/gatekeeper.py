from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
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

#Write requests
class WriteRequest(BaseModel):
    query: str

@app.post("/write")
def receive_write_request(write_request: WriteRequest):

    query = write_request.query

    validation_result = write_validations(query)
    if validation_result == "validated":
        json = {"query": query, "method": "write"}
        trusted_machine_dns = get_running_instances("trusted_machine")[0]['PublicDnsName']
        response = send_request(json, trusted_machine_dns)
    else:
        raise HTTPException(
            status_code=400,
            detail="Validation failed"
        )

    return response

@app.get("/read")
def receive_read_request(
    method: str = Query(..., description="Method of read (direct_hit, random, customized)"),
    query: str = Query(..., description="SQL query to execute")
    ):

    validation_result = read_validations(query, method)
    if validation_result == "validated":
        json = {"query": query, "method": method}
        trusted_machine_dns = get_running_instances("trusted_machine")[0]['PublicDnsName']
        response = send_request(json, trusted_machine_dns)
    else:
        raise HTTPException(
            status_code=400,
            detail="Validation failed"
        )

    return response


def write_validations(query):
    #TODO: Implement validations
    return "validated"


def read_validations(query):
    #TODO: Implement validations
    return "validated"

#DELETE this one
def send_read_request(path, instance_dns):
    url = f"http://{instance_dns}:8000{path}"
    try:
        response = requests.get(url)
        return response.json()
    except requests.RequestException as e:
        print(f"Error sending request to {instance_dns}: {e}")
        return None

def send_request(json, instance_dns):
    url = f"http://{instance_dns}:8000/call_trusted_machine"
    try:
        response = requests.post(url, json=json) # json={"query": query}
    
        return response.json()
    except requests.RequestException as e:
        print(f"Error sending request to {instance_dns}: {e}")
        return None

def get_running_instances(tag = "trusted_machine"):
    ec2_client = boto3.client('ec2', region_name=REGION)
    filters = [{'Name': 'instance-state-name', 'Values': ['running']}]
    response = ec2_client.describe_instances(Filters=filters)
    instances_info = []

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            if instance['Tags'][0]['Value'] == tag:
                instances_info.append({
                    'InstanceId': instance['InstanceId'],
                    'InstanceType': instance['InstanceType'],
                    'PublicDnsName': instance['PublicDnsName'],
                    'Tags': instance['Tags']
                })
    return instances_info