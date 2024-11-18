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

    # Lista de comandos SQL permitidos
    allowed_commands = ("insert", "update", "delete", "create", "drop", "use", "alter", "truncate")

    # Dividir a query em comandos separados pelo ';'
    statements = query.strip().lower().split(';')

    # Validar cada comando
    for statement in statements:
        if statement.strip():  # Ignorar comandos vazios
            command = statement.split()[0]  # Obter a primeira palavra (comando SQL)
            if command not in allowed_commands:
                raise HTTPException(
                    status_code=400,
                    detail=f"Comando não permitido: {command}. Somente {', '.join(allowed_commands).upper()} são permitidos."
                )


    # Executar a query no banco master (manager)
    manager_dns = get_running_instances("manager")[0]['PublicDnsName']
    manager_response = send_write_request_master(query, "/write", manager_dns)

    # Replicar a operação para os workers
    if manager_response["status"] == "success": 
        workers = get_running_instances("worker")
        replication_status = replicate_write(query, "/write", workers)#TODO: try catch
    else:
        replication_status = "failed" 

    return {
        "manager_response": manager_response,
        "replication_status": replication_status
    }

def send_write_request_master(query, path, instance_dns):
    url = f"http://{instance_dns}:8000{path}"
    try:
        response = requests.post(url, json={"query": query})
    
        return response.json()
    except requests.RequestException as e:
        print(f"Error sending request to {instance_dns}: {e}")
        return None
    

def replicate_write(query, path, workers): 

    for worker in workers:
        url = f"http://{worker['PublicDnsName']}:8000{path}"
        try:
            response = requests.post(url, json={"query": query})
        except requests.RequestException as e:
            print(f"Error sending request to {worker['PublicDnsName']}: {e}")
            return "failed"

    return "success"


#Read requests

@app.get("/read")
def receive_read_request(
    method: str = Query(..., description="Method of read (direct_hit, random, customized)"),
    query: str = Query(..., description="SQL query to execute")
    ):

    # Validar se todos os comandos na query são SELECT
    # Lista de comandos SQL permitidos
    allowed_commands = ("select", "use", "show")

    # Dividir a query em comandos separados pelo ';'
    statements = query.strip().lower().split(';')

    # Validar cada comando
    for statement in statements:
        if statement.strip():  # Ignorar comandos vazios
            command = statement.split()[0]  # Obter a primeira palavra (comando SQL)
            if command not in allowed_commands:
                raise HTTPException(
                    status_code=400,
                    detail=f"Comando não permitido: {command}. Somente {', '.join(allowed_commands).upper()} são permitidos."
                )


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
    responseJson = send_read_request(f"/read?query={query}", instances[0]['PublicDnsName'])
    #TODO: Test
    return responseJson

def random_hit(query):
    print("Using Random")
    instances = get_running_instances("worker")
    num = random.randint(0, len(instances) - 1)
    responseJson = send_read_request(f"/read?query={query}", instances[num]['PublicDnsName'])

    return responseJson

def customized(query):
    instances = get_running_instances("worker")
    print("Using Customized")
    best_ping = 10000
    ping = 0
    best_instance = None
    for instance in instances:
        ping = get_ping(instance['PublicDnsName'])
        print(f"ping: {ping}, instance: {instance['InstanceId']}")
        if best_ping >= ping:
            best_ping = ping
            best_instance = instance
    print(f"Best instance: {best_instance['InstanceId']}")

    responseJson = send_read_request(f"/read?query={query}", best_instance['PublicDnsName'])

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

def send_read_request(path, instance_dns):
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
        # Executa o comando ping
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "10", instance_dns],  # -c: Número de pacotes; -W: Timeout em segundos
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            # Processa a saída para obter o tempo de ping
            for line in result.stdout.split("\n"):
                if "time=" in line:
                    result = float(line.split("time=")[1].split(" ")[0])
                    return result  # Extrai o tempo em milissegundos
        else:
            print(f"Erro ao pingar {instance_dns}: {result.stderr.strip()}")
            return float('inf')
    except Exception as e:
        print(f"Erro ao executar o ping: {e}")
        return float('inf')

    

