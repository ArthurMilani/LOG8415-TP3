from pathlib import Path
import sys
import boto3
import paramiko
import os
from scp import SCPClient

parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))


from constants import AWS_CREDENTIALS_FILE, PRIVATE_KEY_FILE, REGION, REMOTE_APP_PATH, REMOTE_AWS_CREDENTIALS_PATH, LOCAL_WORKER_PATH, LOCAL_MANAGER_PATH, LOCAL_PROXY_PATH, TRUSTED_SECURITY_GROUP_NAME, LOCAL_TRUSTED_PATH, LOCAL_GATEKEEPER_PATH

def get_running_instances(ec2_client):
    filters = [{'Name': 'instance-state-name', 'Values': ['running']}]
    response = ec2_client.describe_instances(Filters=filters)
    workers = []
    managers = []
    proxies = []
    gatekeepers = []
    trusteds = []

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            if instance['Tags'][0]['Value'] == 'worker':
                workers.append({
                    'InstanceId': instance['InstanceId'],
                    'InstanceType': instance['InstanceType'],
                    'PublicDnsName': instance['PublicDnsName']
                })
            elif instance['Tags'][0]['Value'] == 'manager':
                managers.append({
                    'InstanceId': instance['InstanceId'],
                    'InstanceType': instance['InstanceType'],
                    'PublicDnsName': instance['PublicDnsName']
                })
            elif instance['Tags'][0]['Value'] == 'proxy':
                proxies.append({
                    'InstanceId': instance['InstanceId'],
                    'InstanceType': instance['InstanceType'],
                    'PublicDnsName': instance['PublicDnsName']
                })
            elif instance['Tags'][0]['Value'] == 'gatekeeper':
                gatekeepers.append ({
                    'InstanceId': instance['InstanceId'],
                    'InstanceType': instance['InstanceType'],
                    'PublicDnsName': instance['PublicDnsName'],
                    'PrivateIpAddress': instance['PrivateIpAddress']
                })
            elif instance['Tags'][0]['Value'] == 'trusted_machine':
                trusteds.append({
                    'InstanceId': instance['InstanceId'],
                    'InstanceType': instance['InstanceType'],
                    'PublicDnsName': instance['PublicDnsName'],
                    'PrivateIpAddress': instance['PrivateIpAddress']
                })
            
    return workers, managers, proxies, gatekeepers, trusteds

def get_target_group_instances(target_group_arn, elbv2_client):
    """Retrieve the instance IDs of all instances in a given target group."""
    response = elbv2_client.describe_target_health(TargetGroupArn=target_group_arn)
    return [target['Target']['Id'] for target in response['TargetHealthDescriptions']]

def create_ssh_client(instance_dns):
    """Create an SSH client to connect to the instance."""
    key = paramiko.RSAKey.from_private_key_file(str(PRIVATE_KEY_FILE))
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {instance_dns}...")
    ssh.connect(hostname=instance_dns, username='ubuntu', pkey=key)
    return ssh

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

def run_remote_commands(ssh, file_type, gatekeeper_ip):
    """Run commands on the remote instance to install dependencies and run the app."""
    commands = []
    if file_type == "worker" or file_type == "manager":
        commands = [
            # "sudo apt update -y",
            # "sudo apt install python3 python3-pip -y",
            # "sudo apt install -y python3-uvicorn",
            # "sudo apt install -y python3-fastapi",
            # "sudo apt install -y python3-boto3",
            #"kill -9 $(lsof -t -i :8000)",
            #"python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 > /home/ubuntu/app.log 2>&1 &"
            # "sudo apt-get update -y", #Uncomment from here
            # "sudo apt-get install mysql-server -y",
            # "wget -N https://downloads.mysql.com/docs/sakila-db.tar.gz",
            # "tar -xzvf sakila-db.tar.gz",
            # "sudo mysql -u root -e 'CREATE DATABASE sakila;'", #TODO: Create Table
            # "sudo mysql -u root sakila < sakila-db/sakila-schema.sql",
            # "sudo mysql -u root sakila < sakila-db/sakila-data.sql",
            # "sudo apt install python3 python3-pip -y",
            # "sudo apt install -y python3-uvicorn",
            # "sudo apt install -y python3-fastapi",
            # "sudo apt install -y python3-boto3",
            # "kill -9 $(lsof -t -i :8000)",
            # f"python3 -m uvicorn {file_type}:app --host 0.0.0.0 --port 8000 > /home/ubuntu/app.log 2>&1 &",
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
            f"sudo iptables -A INPUT -p tcp --dport 8000 -s {gatekeeper_ip} -j ACCEPT", # Allow traffic from gatekeeper
            #f"sudo iptables -A INPUT -p tcp --dport 22 -s {gatekeeper_ip} -j ACCEPT", # Allow SSH traffic TODO: Uncomment
            "sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT", # Allow SSH traffic TODO:REMOVE
            "sudo iptables -A INPUT -p icmp -j ACCEPT", # Allow ICMP traffic for console TODO:REMOVE
            "sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT", # Allow established connections
            #"sudo iptables -A INPUT -j DROP", # Drop all other traffic TODO: Uncomment
        ]
            
    
    for command in commands:
        print(f"Executing: {command}")
        stdin, stdout, stderr = ssh.exec_command(command)
        # print(stdout.read().decode())
        print(stderr.read().decode())
        
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
    
def deploy_to_instance(instance_dns):
    """Deploy AWS credentials and start the FastAPI app."""
    try:
        ssh = create_ssh_client(instance_dns)
        setup_aws_credentials(ssh)


    except Exception as e:
        print(f"Failed to deploy on {instance_dns}: {str(e)}")
    finally:
        ssh.close()

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


def deploy_files():
    # Initialize AWS clients
    ec2 = boto3.client('ec2', region_name=REGION)
    #TODO: Adapt the code to deploy the right files to the right instances
    # Get running instances
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

    print(f"TRUSTEDS: {trusteds}")
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



    # for instance in instances:
    #     instance_id = instance['InstanceId']
    #     instance_dns = instance['PublicDnsName']
    #     instance_type = instance['InstanceType']

        # Deploy to instances in micro-target-group
        # print(f"Deploying to micro-target-group instance: {instance_dns}")
        # deploy_script_via_scp(instance_dns, LOCAL_FASTAPI_CLUSTER1_PATH )

        # Deploy to large-target-group
        # elif instance_id in large_target_instances:
        #     if instance_type == LARGE_INSTANCE_TYPE and large_instance_dns is None: #deploy alb to first instance in large target group
        #         print(f"Deploying ALB credentials to large instance: {instance_dns}")
        #         deploy_to_instance(instance_dns)
        #         print(f"Deploying ALB script to large instance: {instance_dns}")
        #         deploy_script_via_scp(instance_dns, LOCAL_ALB_APP_PATH)
        #         large_instance_dns = instance_dns  # Only deploy ALB script once
        #     else:
        #         print(f"Deploying to large-target-group instance: {instance_dns}")
        #         deploy_script_via_scp(instance_dns, LOCAL_FASTAPI_CLUSTER2_PATH)
    
    # if large_instance_dns:
    #     print(f"Large instance running ALB script: {large_instance_dns}")
    #     return large_instance_dns
    # else:
    #     print("No large instance found or ALB script deployed.")

    #Update SSH Rule
    update_ssh_rule(ec2, gatekeeper['PrivateIpAddress'])

deploy_files() #TODO: Remove
    
#TODO: Specify the SSH IP permission only for the gatekeeper