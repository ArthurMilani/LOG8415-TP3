from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from pathlib import Path
from ping3 import ping
import sys
import boto3
import uvicorn
import logging
import requests
import time
import random

parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

from constants import REGION

# Create FastAPI app
app = FastAPI()


#Write requests
class WriteRequest(BaseModel):
    query: str


@app.post("/write")
def receive_request(write_request: WriteRequest):

    query = write_request.query

    # Validar se a query é de escrita (INSERT, UPDATE, DELETE)
    if not query.strip().lower().startswith(("insert", "update", "delete")):
        raise HTTPException(status_code=400, detail="Only INSERT, UPDATE, or DELETE queries are allowed for writes")

    # Executar a query no banco master (manager)
    manager_response = write_to_master_db(query) #TODO: try catch

    # Replicar a operação para os workers
    if manager_response == "success": #TODO - verificar se a resposta do manager é um sucesso
        replication_status = replicate_write(query) #TODO: try catch
    else:
        replication_status = "failed" 

    return {
        "manager_response": manager_response,
        "replication_status": replication_status
    }

def write_to_master_db(query):
    #TODO
    #The necessity of replication will ve in the return of the master response
    return 20 + 20

def replicate_write(query): 
    #TODO
    return 20 + 20


#Read requests

@app.get("/read")
def receive_request(
    method: str = Query(..., description="Method of read (direct_hit, random, customized)"),
    query: str = Query(..., description="SQL query to execute")
    ):

    if not query.strip().lower().startswith("select"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed for reads")

    if method == "direct_hit":
        return direct_hit(query)
    elif method == "random":
        return random_hit(query)
    elif method == "customized":
        return customized(query)
    else:
        raise HTTPException(
            status_code=400, 
            detail="Invalid method. Choose from: direct_hit, random, customized"
            )

def direct_hit(query):
    print("Using Direct hit")
    instances = get_running_instances("manager")
    print(f"Instances: {instances}")
    responseJson = send_request_to_instance(f"/read?query={query}", instances[0]['PublicDnsName'])
    #TODO: Test
    return responseJson

def random_hit(query):
    print("Using Random")
    instances = get_running_instances("worker")
    num = random.randint(0, len(instances) - 1)
    responseJson = send_request_to_instance(f"/read?query={query}", instances[num]['PublicDnsName'])

    return responseJson

def customized(query):
    instances = get_running_instances("worker")
    print("Using Customized")
    best_ping = 10
    ping = 0
    best_instance = None
    for instance in instances:
        ping = get_ping(instance['PublicDnsName'])
        print(f"ping: {ping}, instance: {instance['InstanceId']}")
        if best_ping >= ping:
            best_ping = ping
            best_instance = instance
    print(f"Best instance: {best_instance['InstanceId']}")

    responseJson = send_request_to_instance(f"/read?query={query}", best_instance['PublicDnsName'])

    return responseJson


def get_running_instances(tag):
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

def send_request_to_instance(path, instance_dns):
    url = f"http://{instance_dns}:8000{path}"
    try:
        response = requests.get(url)
        return response.json()
    except requests.RequestException as e:
        print(f"Error sending request to {instance_dns}: {e}")
        return None
    
#TODO: Test the new craation of the security group with the new rules
def get_ping(instance_dns):
    try:
        return ping(instance_dns, timeout=10)
    except Exception as e:
        print(f"Erro ao pingar {instance_dns}: {e}")
        return float('inf')

    

