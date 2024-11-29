from pathlib import Path
import sys
import boto3
import paramiko
import os
from scp import SCPClient

parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))


from constants import AWS_CREDENTIALS_FILE, PRIVATE_KEY_FILE, REGION, REMOTE_APP_PATH, REMOTE_AWS_CREDENTIALS_PATH, LOCAL_WORKER_PATH, LOCAL_MANAGER_PATH, LOCAL_PROXY_PATH, TRUSTED_SECURITY_GROUP_NAME, LOCAL_TRUSTED_PATH, LOCAL_GATEKEEPER_PATH

# def get_running_instances(ec2_client):
#     filters = [{'Name': 'instance-state-name', 'Values': ['running']}]
#     response = ec2_client.describe_instances(Filters=filters)
#     workers = []
#     managers = []
#     proxies = []
#     gatekeepers = []
#     trusteds = []

#     for reservation in response['Reservations']:
#         for instance in reservation['Instances']:
#             if instance['Tags'][0]['Value'] == 'worker':
#                 workers.append({
#                     'InstanceId': instance['InstanceId'],
#                     'InstanceType': instance['InstanceType'],
#                     'PublicDnsName': instance['PublicDnsName'],
#                     'PrivateIpAddress': instance['PrivateIpAddress']
#                 })
#             elif instance['Tags'][0]['Value'] == 'manager':
#                 managers.append({
#                     'InstanceId': instance['InstanceId'],
#                     'InstanceType': instance['InstanceType'],
#                     'PublicDnsName': instance['PublicDnsName'],
#                     'PrivateIpAddress': instance['PrivateIpAddress']
#                 })
#             elif instance['Tags'][0]['Value'] == 'proxy':
#                 proxies.append({
#                     'InstanceId': instance['InstanceId'],
#                     'InstanceType': instance['InstanceType'],
#                     'PublicDnsName': instance['PublicDnsName'],
#                     'PrivateIpAddress': instance['PrivateIpAddress']
#                 })
#             elif instance['Tags'][0]['Value'] == 'gatekeeper':
#                 gatekeepers.append ({
#                     'InstanceId': instance['InstanceId'],
#                     'InstanceType': instance['InstanceType'],
#                     'PublicDnsName': instance['PublicDnsName'],
#                     'PrivateIpAddress': instance['PrivateIpAddress']
#                 })
#             elif instance['Tags'][0]['Value'] == 'trusted_machine':
#                 trusteds.append({
#                     'InstanceId': instance['InstanceId'],
#                     'InstanceType': instance['InstanceType'],
#                     'PublicDnsName': instance['PublicDnsName'],
#                     'PrivateIpAddress': instance['PrivateIpAddress']
#                 })
            
#     return workers, managers, proxies, gatekeepers, trusteds


#Get all running instances relevant data
def get_running_instances(ec2_client):
    filters = [{'Name': 'instance-state-name', 'Values': ['running']}]
    response = ec2_client.describe_instances(Filters=filters)
    tag_to_list = {
        'worker': [],
        'manager': [],
        'proxy': [],
        'gatekeeper': [],
        'trusted_machine': []
    }
    for reservation in response.get('Reservations', []):
        for instance in reservation.get('Instances', []):
            tag_value = next(
                (tag['Value'] for tag in instance.get('Tags', []) if 'Value' in tag), 
                None
            )
            if tag_value in tag_to_list:
                tag_to_list[tag_value].append({
                    'InstanceId': instance.get('InstanceId'),
                    'InstanceType': instance.get('InstanceType'),
                    'PublicDnsName': instance.get('PublicDnsName'),
                    'PrivateIpAddress': instance.get('PrivateIpAddress')
                })
    return tag_to_list['worker'], tag_to_list['manager'], tag_to_list['proxy'], tag_to_list['gatekeeper'], tag_to_list['trusted_machine']


# Create an SSH client to connect to the instance
def create_ssh_client(instance_dns):
    key = paramiko.RSAKey.from_private_key_file(str(PRIVATE_KEY_FILE))
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {instance_dns}...")
    ssh.connect(hostname=instance_dns, username='ubuntu', pkey=key)
    return ssh


# Copy the local script to the remote instance and call the method to run the script
def deploy_script_via_scp(instance_dns, file_type, local_app_path, gatekeeper_ip=None):
    """Use SCP to copy the local script to the remote instance."""
    try:
        # Create SSH client
        ssh = create_ssh_client(instance_dns)
        
        # SCP the file to the remote instance
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(local_app_path, REMOTE_APP_PATH)
            print(f"Successfully copied {local_app_path} to {instance_dns}:{REMOTE_APP_PATH}")
        
        # Run the script on the remote instance
        run_remote_commands(ssh, file_type, gatekeeper_ip)
        
    except Exception as e:
        print(f"Failed to deploy on {instance_dns}: {str(e)}")
    finally:
        ssh.close()


# Run commands on the remote instance to install dependencies and run the app
def run_remote_commands(ssh, file_type, gatekeeper_ip):
    """Run commands on the remote instance to install dependencies and run the app."""
    commands = []
    if file_type == "worker" or file_type == "manager":
        commands = [
            "sudo apt-get update -y",
            "sudo apt-get install mysql-server -y",
            "wget -N https://downloads.mysql.com/docs/sakila-db.tar.gz",
            "tar -xzvf sakila-db.tar.gz",
            "sudo mysql -u root -e 'CREATE DATABASE sakila;'",
            "sudo mysql -u root sakila < sakila-db/sakila-schema.sql",
            "sudo mysql -u root sakila < sakila-db/sakila-data.sql",
            "sudo apt install python3 python3-pip -y",
            "sudo apt install -y python3-uvicorn",
            "sudo apt install -y python3-fastapi",
            "sudo apt install -y python3-boto3",
            "kill -9 $(lsof -t -i :8000)",
            f"python3 -m uvicorn {file_type}:app --host 0.0.0.0 --port 8000 > /home/ubuntu/app.log 2>&1 &",
        ]
    elif file_type == "proxy" or file_type == "gatekeeper":
        commands = [
            "sudo apt-get update -y",
            "sudo apt-get install python3 python3-pip -y",
            "sudo apt-get install -y python3-uvicorn",
            "sudo apt-get install -y python3-fastapi",
            "sudo apt-get install -y python3-boto3",
            "kill -9 $(lsof -t -i :8000)",
            f"python3 -m uvicorn {file_type}:app --host 0.0.0.0 --port 8000 > /home/ubuntu/app.log 2>&1 &",
        ]
    elif file_type == "trusted_machine":
        commands = [
            "sudo apt-get update -y",
            "sudo apt-get install python3 python3-pip -y",
            "sudo apt-get install -y python3-uvicorn",
            "sudo apt-get install -y python3-fastapi",
            "sudo apt-get install -y python3-boto3",
            "kill -9 $(lsof -t -i :8000)",
            f"python3 -m uvicorn {file_type}:app --host 0.0.0.0 --port 8000 > /home/ubuntu/app.log 2>&1 &",
            # f"sudo iptables -A INPUT -p tcp --dport 8000 -s {gatekeeper_ip} -j ACCEPT", # Allow traffic from gatekeeper
            # f"sudo iptables -A INPUT -p tcp --dport 22 -s {gatekeeper_ip} -j ACCEPT", # Allow SSH traffic
            # "sudo iptables -A INPUT -p icmp -j ACCEPT", # Allow ICMP traffic for console TODO:REMOVE
            # "sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT", # Allow established connections
            # "sudo iptables -A INPUT -j DROP", # Drop all other traffic TODO: Uncomment
        ]
    #Execute the commands
    for command in commands:
        print(f"Executing: {command}")
        stdin, stdout, stderr = ssh.exec_command(command)
        print(stderr.read().decode())
        

# Create the .aws directory, upload credentials, and set file permissions
def setup_aws_credentials(ssh):
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

    # Change the file permissions for the credentials file
    ssh.exec_command(f"chmod 600 {REMOTE_AWS_CREDENTIALS_PATH}")
    print(f"File permissions set for {REMOTE_AWS_CREDENTIALS_PATH}")


#Deployment of AWS credentials
def deploy_to_instance(instance_dns):
    try:
        ssh = create_ssh_client(instance_dns)
        setup_aws_credentials(ssh)
    except Exception as e:
        print(f"Failed to deploy on {instance_dns}: {str(e)}")
    finally:
        ssh.close()


# Update the SSH rule to allow traffic only from the selected instances
def update_ssh_rule(ec2_client, gatekeeper_ip):
    try:
        response = ec2_client.describe_security_groups(
                Filters=[{"Name": "group-name", "Values": [TRUSTED_SECURITY_GROUP_NAME]}]
            )
        sg_ip = response["SecurityGroups"][0]["GroupId"]
        ec2_client.revoke_security_group_ingress(
            GroupId=sg_ip,
            IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': "0.0.0.0/0"}]
                    }
            ]
        )
        ec2_client.authorize_security_group_ingress(
            GroupId=sg_ip,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': f"{gatekeeper_ip}/32"}]
                }
            ]
        )
    except Exception as e:
        print(f"Failed to update SSH rule: {e}")


#Deploy the files to the right instances.
#In some cases, we also deploy the AWS credentials and update the security group rules
def deploy_files():
    ec2 = boto3.client('ec2', region_name=REGION)
    # Get all running instances
    workers, managers, proxies, gatekeepers, trusteds = get_running_instances(ec2_client=ec2)

    for worker in workers:
        print (f"Deploying to worker instance: {worker['PublicDnsName']}")
        deploy_script_via_scp(worker['PublicDnsName'], "worker", LOCAL_WORKER_PATH)
        
    for manager in managers:
        print (f"Deploying to manager instance: {manager['PublicDnsName']}")
        deploy_script_via_scp(manager['PublicDnsName'], "manager", LOCAL_MANAGER_PATH)

    for proxy in proxies:
        print(f"Deploying Proxy Credentials to large instance: {proxy['PublicDnsName']}")
        deploy_to_instance(proxy['PublicDnsName'])
        print (f"Deploying to proxy instance: {proxy['PublicDnsName']}")
        deploy_script_via_scp(proxy['PublicDnsName'], "proxy", LOCAL_PROXY_PATH)

    for trusted_machine in trusteds:
        print(f"Deploying Trusted Machine Credentials to large instance: {trusted_machine['PublicDnsName']}")
        deploy_to_instance(trusted_machine['PublicDnsName'])
        print(f"Deploying to trusted machine instance: {trusted_machine['PublicDnsName']}")
        deploy_script_via_scp(trusted_machine['PublicDnsName'], "trusted_machine", LOCAL_TRUSTED_PATH, gatekeepers[0]['PrivateIpAddress'])

    for gatekeeper in gatekeepers:
        print(f"Deploying Gatekeeper Credentials to large instance: {gatekeeper['PublicDnsName']}")
        deploy_to_instance(gatekeeper['PublicDnsName'])
        print(f"Deploying to gatekeeper instance: {gatekeeper['PublicDnsName']}")
        deploy_script_via_scp(gatekeeper['PublicDnsName'], "gatekeeper", LOCAL_GATEKEEPER_PATH)

    #Update SSH Rule for trusted machine and cluster
    update_ssh_rule(ec2, gatekeeper['PrivateIpAddress'])

deploy_files() #TODO: Remove