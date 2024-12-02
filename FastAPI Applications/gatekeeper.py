from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from pathlib import Path
import sys
import boto3
import uvicorn
import requests
import re
from contextlib import asynccontextmanager


parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))
REGION = "us-east-1"

# Global variable to store the trusted machine DNS
@asynccontextmanager
async def lifespan(app: FastAPI): #Using lifespan in the beginning of the application to avoid sending too many requests to the AWS API
    print("Initializing appliacation!")
    await define_instances_data()
    yield

async def define_instances_data():
    global trusted_machine_dns
    trusted_machine_dns = get_running_instances("trusted_machine")[0]['PublicDnsName']

# Create FastAPI app
app = FastAPI(lifespan=lifespan)


#Write requests
class WriteRequest(BaseModel):
    query: str


#Receive write requests from the internet
@app.post("/write")
def receive_write_request(write_request: WriteRequest):
    query = write_request.query
    validation_result = write_validations(query)
    if validation_result == "validated":
        json = {"query": query, "method": "write"}
        response = send_request(json, trusted_machine_dns)
    else:
        raise HTTPException(
            status_code=400,
            detail="Validation failed"
        )
    return response


#Receive read requests from the internet
@app.get("/read")
def receive_read_request(
    method: str = Query(..., description="Method of read (direct_hit, random, customized)"),
    query: str = Query(..., description="SQL query to execute")
    ):
    validation_result = read_validations(query, method)
    if validation_result == "validated":
        json = {"query": query, "method": method}
        response = send_request(json, trusted_machine_dns)
    else:
        raise HTTPException(
            status_code=400,
            detail="Validation failed"
        )
    return response


# Validate write requests
def write_validations(query):
    allowed_commands = ("insert", "update", "delete", "create", "drop") #Allowed commands for write
    statement = query.strip().lower()
    if statement.strip():  # Ignore empty commands
        command = statement.split()[0]  # Get the first word (SQL command)
        if command not in allowed_commands:
            return "not validated"
    if sql_injection_validation(query):
        return "not validated"
    return "validated"


# Validate read requests
def read_validations(query):
    allowed_commands = ("select", "use", "show") #Allowed commands for read
    statement = query.strip().lower()
    if statement.strip():  # Ignore empty commands
        command = statement.split()[0]  # Get the first word (SQL command)
        if command not in allowed_commands:
            return "not validated"
    if sql_injection_validation(query):
        return "not validated"
    return "validated"


#Check for SQL Injection patterns
def sql_injection_validation(query):
    suspect_patterns = [
        r"(\||&&|\|\||>|<|\$|\`)",  #Suspect characters
        r"(--|;|#)",                #Comments  
        r"(\'.*?\b(=|or|and)\b)"    #Condition manipulation
        r"(^|\s)(rm|ls|cat|echo|mkdir|wget|curl|chmod|chown|sudo)(\s|$)" #Shell commands
    ]   
    for padrao in suspect_patterns:
        if re.search(padrao, query, re.IGNORECASE):
            return True
    return False


# Send request to the trusted machine
def send_request(json, instance_dns):
    url = f"http://{instance_dns}:8000/call_trusted_machine"
    try:
        response = requests.post(url, json=json) # json={"query": query}
        return response.json()
    except requests.RequestException as e:
        print(f"Error sending request to {instance_dns}: {e}")
        return {"status": "failed", "message": str(e)}


# Get running instances, in this case, the trusted machine
def get_running_instances(tag = "trusted_machine"):
    print("Ola")
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


