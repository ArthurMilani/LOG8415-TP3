from pathlib import Path
import mysql.connector
from mysql.connector import Error
import sys
import subprocess
import boto3
import paramiko
import os
from scp import SCPClient
import uuid

parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

from constants import REGION, DB_CONFIG, PRIVATE_KEY_FILE, AWS_CREDENTIALS_FILE, REMOTE_AWS_CREDENTIALS_PATH, LOCAL_INFO_JSON_PATH

def get_running_instances(ec2_client):
    filters = [{'Name': 'instance-state-name', 'Values': ['running']}]
    response = ec2_client.describe_instances(Filters=filters)
    instances_info = []

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instances_info.append({
                'InstanceId': instance['InstanceId'],
                'InstanceType': instance['InstanceType'],
                'PublicDnsName': instance['PublicDnsName'],
                'Tags': instance['Tags']
            })
    print(instances_info)

def database(query):
    # try:
    #     connection = mysql.connector.connect(**DB_CONFIG)
    #     if connection.is_connected():
    #         print("Conexão bem-sucedida ao banco de dados!")
    # except Error as e:
    #     print(f"Erro ao conectar ao banco de dados: {e}")
    # finally:
    #     if connection.is_connected():
    #         connection.close()
    result = subprocess.run(
            ['sudo', 'mysql', '-e', query],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    try:
        # Executa o comando MySQL diretamente no terminal
        result = subprocess.run(
            ['sudo', 'mysql', '-e', query],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            print(f"Resultado: {result}")
        else:
            print(f"Erro: {result.stderr}")
    except Exception as e:
        print(f"Erro ao executar a query: {e}")

# ec2 = boto3.client('ec2', region_name=REGION)
# get_running_instances(ec2_client=ec2)

def deploy_to_instance(instance_dns):
    """Deploy AWS credentials and start the FastAPI app."""
    try:
        ssh = create_ssh_client(instance_dns)
        setup_aws_credentials(ssh)


    except Exception as e:
        print(f"Failed to deploy on {instance_dns}: {str(e)}")
    finally:
        ssh.close()

def create_ssh_client(instance_dns):
    """Create an SSH client to connect to the instance."""
    key = paramiko.RSAKey.from_private_key_file(str(PRIVATE_KEY_FILE))
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {instance_dns}...")
    ssh.connect(hostname=instance_dns, username='ubuntu', pkey=key)
    return ssh

def setup_aws_credentials(ssh):
    """Create the .aws directory, upload credentials, and set file permissions."""
    commands = [
        "mkdir -p /home/ubuntu/.aws",  # Create .aws directory
    ]
    
    for command in commands:
        print(f"Executing: {command}")
        stdin, stdout, stderr = ssh.exec_command(command)
        print(stderr.read().decode())

    # SCP the credentials file to the remote instance
    with SCPClient(ssh.get_transport()) as scp:
        scp.put(AWS_CREDENTIALS_FILE, REMOTE_AWS_CREDENTIALS_PATH)
        print(f"Successfully copied AWS credentials to {REMOTE_AWS_CREDENTIALS_PATH}")
        
        # Also SCP the JSON file to the remote instance
        # scp.put(LOCAL_INFO_JSON_PATH, '/home/ubuntu/instance_info.json')
        # print("Successfully copied JSON file to /home/ubuntu/instance_info.json")

    # Change the file permissions for the credentials file
    ssh.exec_command(f"chmod 600 {REMOTE_AWS_CREDENTIALS_PATH}")
    print(f"File permissions set for {REMOTE_AWS_CREDENTIALS_PATH}")

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
                    print (result)
                    return result  # Extrai o tempo em milissegundos
        else:
            print(f"Erro ao pingar {instance_dns}: {result.stderr.strip()}")
            return float('inf')
    except Exception as e:
        print(f"Erro ao executar o ping: {e}")
        return float('inf')
    
# def get_ping(instance_dns):
#     try:
#         return ping(instance_dns, timeout=10)
#     except Exception as e:
#         print(f"Erro ao pingar {instance_dns}: {e}")
#         return float('inf')

# query = """
# USE sakila;
# INSERT INTO example_table (name, age)
# VALUES ('Alice', 30), ('Bob', 25);
# """
# deploy_to_instance("ec2-18-213-4-237.compute-1.amazonaws.com")
# get_ping("ec2-3-80-151-238.compute-1.amazonaws.com")
