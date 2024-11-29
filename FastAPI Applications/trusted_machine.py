from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from pathlib import Path
import sys
import boto3
import uvicorn
import requests


parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))
REGION = "us-east-1"
# Create FastAPI app
app = FastAPI()


#Write requests
class WriteRequest(BaseModel):
    query: str
    method: str #Write, direct_hit, random, customized


#Receive valid requests from the gatekeeper
@app.post("/call_trusted_machine")
def receive_write_request(write_request: WriteRequest):
    response = None
    query = write_request.query
    method = write_request.method
    proxy_dns = get_running_instances("proxy")[0]['PrivateIpAddress']
    if method == "write":
        response = send_write_request(query, "/write", proxy_dns)
    elif method == "direct_hit" or method == "random" or method == "customized":
        response = send_read_request(f"/read?method={method}&query={query}", proxy_dns)

    return response


#Send read request to the proxy
def send_read_request(path, instance_dns):
    url = f"http://{instance_dns}:8000{path}"
    try:
        response = requests.get(url)
        return response.json()
    except requests.RequestException as e:
        print(f"Error sending request to {instance_dns}: {e}")
        return None


#Send write request to the proxy
def send_write_request(query, path, instance_dns):
    url = f"http://{instance_dns}:8000{path}"
    try:
        response = requests.post(url, json={"query": query})
        return response.json()
    except requests.RequestException as e:
        print(f"Error sending request to {instance_dns}: {e}")
        return {"status": "failed", "message": str(e)}


#Get the filtrated instaces by tag
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
                    'PrivateIpAddress': instance['PrivateIpAddress'],
                    'Tags': instance['Tags']
                })
    return instances_info