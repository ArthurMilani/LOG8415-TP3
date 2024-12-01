from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from pathlib import Path
import sys
import boto3
import subprocess
import uvicorn
import requests
import random


parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))
REGION = "us-east-1"

# Global variables to store the instances data
@asynccontextmanager
async def lifespan(app: FastAPI): #Using lifespan in the beginning of the application to avoid sending too many requests to the AWS API
    await define_instances()
    yield

async def define_instances():
    global workers
    global manager
    workers = get_running_instances("worker")
    manager = get_running_instances("manager")

# Create FastAPI app
app = FastAPI(lifespan=lifespan)


#Write requests
class WriteRequest(BaseModel):
    query: str


#Receive the write request
@app.post("/write")
def receive_write_request(write_request: WriteRequest):
    query = write_request.query
    # The first execution of the write request is done in the manager
    #manager_dns = get_running_instances("manager")[0]['PublicDnsName']
    manager_dns = manager[0]['PublicDnsName']
    manager_response = send_write_request_master(query, "/write", manager_dns)
    # If the manager response is successful, the write request is replicated to the workers
    if manager_response["status"] == "success": 
        #workers = get_running_instances("worker")
        replication_response = replicate_write(query, "/write", workers)
        # If the replication is successful, the response is returned
        if replication_response["status"] == "failed":
            print("Replication failed")
            raise HTTPException(
                status_code=400,
                detail="Replication failed: " + replication_response["message"]
            )
    else:
        print("Manager response failed")
        raise HTTPException(
            status_code=400,
            detail="Manager response failed: " + manager_response["message"]
        )
    # If everything is successful, the response is returned
    return {
        "manager_response": "success",
        "replication_status": "success"
    }


#Write request to the manager
def send_write_request_master(query, path, instance_dns):
    url = f"http://{instance_dns}:8000{path}"
    try:
        response = requests.post(url, json={"query": query})
    
        return response.json()
    except requests.RequestException as e:
        print(f"Error sending request to {instance_dns}: {e}")
        return {"status": "failed", "message": str(e)}
    

#Replicate the write request to the workers
def replicate_write(query, path, workers): 
    for worker in workers:
        url = f"http://{worker['PublicDnsName']}:8000{path}"
        try:
            requests.post(url, json={"query": query})
        except requests.RequestException as e:
            print(f"Error sending request to {worker['PublicDnsName']}: {e}")
            return {"status": "failed", "message": str(e)}

    return {"status": "success"}


#Read requests
@app.get("/read")
def receive_read_request(
    method: str = Query(..., description="Method of read (direct_hit, random, customized)"),
    query: str = Query(..., description="SQL query to execute")
    ):
    #Select the method to be used according to the parameter
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


#Send the read request to the manager
def direct_hit(query):
    print("Using Direct hit")
    #instances = get_running_instances("manager")
    print(f"Instances: {manager}")
    responseJson = send_read_request(f"/read?query={query}", manager[0]['PublicDnsName'])
    if responseJson["status"] == "failed":
        raise HTTPException(
            status_code=400,
            detail="Direct hit failed: " + responseJson["message"]
        )
    return responseJson


#Send the read request to a random worker
def random_hit(query):
    print("Using Random")
    #instances = get_running_instances("worker")
    num = random.randint(0, len(workers) - 1)
    responseJson = send_read_request(f"/read?query={query}", workers[num]['PublicDnsName'])
    if responseJson["status"] == "failed":
        raise HTTPException(
            status_code=400,
            detail="Random hit failed: " + responseJson["message"]
        )
    return responseJson


#Send the read request to the worker with the lowest ping
def customized(query):
    #workers = get_running_instances("worker")
    print("Using Customized")
    best_ping = 10000
    ping = 0
    best_instance = None
    #Getting the ping of each worker
    for instance in workers:
        ping = get_ping(instance['PublicDnsName'])
        print(f"ping: {ping}, instance: {instance['InstanceId']}")
        if best_ping >= ping:
            best_ping = ping
            best_instance = instance
    print(f"Best instance: {best_instance['InstanceId']}")
    responseJson = send_read_request(f"/read?query={query}", best_instance['PublicDnsName'])
    if responseJson["status"] == "failed":
        raise HTTPException(
            status_code=400,
            detail="Customized failed: " + responseJson["message"]
        )
    return responseJson


#Get the running instances with the specified tag
def get_running_instances(tag):
    ec2_client = boto3.client('ec2', region_name=REGION)
    filters = [{'Name': 'instance-state-name', 'Values': ['running']}]
    response = ec2_client.describe_instances(Filters=filters)
    instances_info = []
    #Filter the instances with the specified tag
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


#Send the read request to the specified instance
def send_read_request(path, instance_dns):
    url = f"http://{instance_dns}:8000{path}"
    try:
        response = requests.get(url)
        return response.json()
    except requests.RequestException as e:
        print(f"Error sending request to {instance_dns}: {e}")
        return {"status": "failed", "message": str(e)}
    

#Get the ping of the instance
def get_ping(instance_dns):
    try:
        # Execute the ping command
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "10", instance_dns],  # -c: Package number; -W: Timeout
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            # Get the time from the result
            for line in result.stdout.split("\n"):
                if "time=" in line:
                    result = float(line.split("time=")[1].split(" ")[0])
                    return result 
        else:
            print(f"Ping error to {instance_dns}: {result.stderr.strip()}")
            return float('inf')
    except Exception as e:
        print(f"Error trying to execute ping: {e}")
        return float('inf')

