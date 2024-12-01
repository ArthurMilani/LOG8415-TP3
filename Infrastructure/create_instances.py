from pathlib import Path
import sys
import boto3
from botocore.exceptions import ClientError
import os

parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))
from constants import KEY_PAIR_NAME, REGION, SECURITY_GROUP_NAME, GATEKEEPER_IPCONFIG, TRUSTED_SECURITY_GROUP_NAME, MICRO_INSTANCE, LARGE_INSTANCE, CLUSTER_SECURITY_GROUP_NAME


# Count the number of currently running instances
def count_running_instances(ec2_client):
    """Count the number of currently running instances."""
    try:
        response = ec2_client.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )
        running_instances = sum(len(reservation["Instances"]) for reservation in response["Reservations"])
        print(f"Current running instances: {running_instances}")
        return running_instances
    except ClientError as e:
        print(f"Error retrieving running instances: {e}")
        return 0


# Create Key Pair for SSH access
def create_key_pair(ec2_client):
    try:
        response_key_pair = ec2_client.create_key_pair(KeyName=KEY_PAIR_NAME)
        print(f"KEY PAIR ({response_key_pair['KeyPairId']}) created: {response_key_pair['KeyName']}")
        
        # Save the private key to a file
        private_key = response_key_pair['KeyMaterial']
        key_file_path = Path(f'./{KEY_PAIR_NAME}.pem').resolve()
        with open(key_file_path, 'w') as key_file:
            key_file.write(private_key)
        
        # Set appropriate permissions for the key file (Unix-based systems)
        os.chmod(key_file_path, 0o400)
        return KEY_PAIR_NAME
    except ClientError as e:
        if "InvalidKeyPair.Duplicate" in str(e):
            print(f"Key pair '{KEY_PAIR_NAME}' already exists.")
            return KEY_PAIR_NAME
        else:
            print(f"Error creating key pair: {e}")
            return None
        

# Create Security Group if it does not already exist
def create_security_group(ec2_client, security_group_name):
    try:
        response_security_group = ec2_client.create_security_group(
            GroupName=security_group_name, Description="Security group for TP3 EC2 instance"
        )
        security_group_id = response_security_group["GroupId"]
        print(f"Security Group ({security_group_name}) created: {security_group_id}")

        # Set ingress rules for the gatekeeper 
        if security_group_name == SECURITY_GROUP_NAME:
            ec2_client.authorize_security_group_ingress(GroupId=security_group_id, IpPermissions=GATEKEEPER_IPCONFIG)
        return security_group_id
    
    except ClientError as e:
        if "InvalidGroup.Duplicate" in str(e):
            return get_existing_security_group(ec2_client, security_group_name)
        else:
            print(f"Error creating security group: {e}")
            security_group_id = None


# Get existing security group if it already exists
def get_existing_security_group(ec2_client, security_group_name):
    try:
        response = ec2_client.describe_security_groups(
            Filters=[{"Name": "group-name", "Values": [security_group_name]}]
        )
        security_group_id = response["SecurityGroups"][0]["GroupId"]
        print(f"Security Group ({security_group_id}) already exists.")
        return security_group_id

    except ClientError as describe_error:
        print(f"Error retrieving existing security group: {describe_error}")
        security_group_id = None


#Launching all the instances if they are not already running
def launch_instances(ec2_client, security_group_id, trusted_security_group_id, cluster_security_group_id):
    # Check the number of running instances
    if count_running_instances(ec2_client) >= 6:
        print("Skipping instance launch: already 6 instances are running.")
        return
    
    # Parameters for EC2 Instances
    micro_instance = MICRO_INSTANCE
    large_instance = LARGE_INSTANCE
    micro_instance["SecurityGroupIds"] = [cluster_security_group_id]
    large_instance["SecurityGroupIds"] = [cluster_security_group_id]
    instance_params_micro = micro_instance
    instance_params_large = large_instance

    # Launch EC2 Instances
    try:
        # Launch t2.micro instances
        if instance_params_micro["KeyName"] and instance_params_micro["SecurityGroupIds"]:
            # Launch worker instances
            response_micro = ec2_client.run_instances(**instance_params_micro)
            instance_ids_micro = [instance["InstanceId"] for instance in response_micro["Instances"]]
            print(f"Launched EC2 t2.micro worker instances with IDs: {instance_ids_micro}")

            # Wait for the t2.micro worker instances to be in the 'running' state
            waiter = ec2_client.get_waiter('instance_running')
            print("Waiting for t2.micro worker instances to be running...")
            waiter.wait(InstanceIds=instance_ids_micro)
            print("t2.micro worker instances are now running.")
   
            instance_params_micro["TagSpecifications"] = [{'ResourceType': 'instance', 'Tags': [{'Key': 'Role', 'Value': 'manager'}]}]
            instance_params_micro["MinCount"] = 1
            instance_params_micro["MaxCount"] = 1
            
            # Launch manager instance
            response_micro = ec2_client.run_instances(**instance_params_micro)
            instance_ids_micro = [instance["InstanceId"] for instance in response_micro["Instances"]]
            print(f"Launched EC2 t2.micro manager instance with IDs: {instance_ids_micro}")

            # Wait for the t2.micro manager instance to be in the 'running' state
            waiter = ec2_client.get_waiter('instance_running')
            print("Waiting for t2.micro manager instance to be running...")
            waiter.wait(InstanceIds=instance_ids_micro)
            print("t2.micro manager instance is now running.")

        else:
            print(f"Key pair: {KEY_PAIR_NAME}, security group: {security_group_id}, instance_params_micro: {instance_params_micro}")
            print("Skipping t2.micro instance launch due to missing key pair or security group.")

        # Launch t2.large instances, specifying the security group and tag
        if instance_params_large["KeyName"] and instance_params_large["SecurityGroupIds"]:
            # Launch proxy
            response_large = ec2_client.run_instances(**instance_params_large)
            instance_ids_large = [instance["InstanceId"] for instance in response_large["Instances"]]
            print(f"Launched EC2 t2.large proxy instances with ID: {instance_ids_large}")

            # Wait for the proxy instance to be in the 'running' state
            print("Waiting for t2.large instances to be running...")
            waiter.wait(InstanceIds=instance_ids_large)
            print("t2.large instances are now running.")

            #Launch gatekeeper
            instance_params_large["SecurityGroupIds"] = [security_group_id]
            instance_params_large["TagSpecifications"] = [{'ResourceType': 'instance', 'Tags': [{'Key': 'Role', 'Value': 'gatekeeper'}]}]
            response_large = ec2_client.run_instances(**instance_params_large)
            instance_ids_large = [instance["InstanceId"] for instance in response_large["Instances"]]
            print(f"Launched EC2 t2.large gatekeeper instance with IDs: {instance_ids_large}")

            # Wait for the gatekeeper instance to be in the 'running' state
            print("Waiting for t2.large gatekeeper instance to be running...")
            waiter.wait(InstanceIds=instance_ids_large)
            print("t2.large gatekeeper instance is now running.")

            # Launch Trusted Machine
            instance_params_large["SecurityGroupIds"] = [trusted_security_group_id]
            instance_params_large["TagSpecifications"] = [{'ResourceType': 'instance', 'Tags': [{'Key': 'Role', 'Value': 'trusted_machine'}]}]
            response_large = ec2_client.run_instances(**instance_params_large)
            instance_ids_large = [instance["InstanceId"] for instance in response_large["Instances"]]
            print(f"Launched EC2 t2.large trusted machine instance with IDs: {instance_ids_large}")

            # Wait for the t2.large trusted machine instance to be in the 'running' state
            print("Waiting for t2.large trusted machine instance to be running...")
            waiter.wait(InstanceIds=instance_ids_large)
            print("t2.large trusted machine instance is now running.")

        else:
            print(f"Key pair: {KEY_PAIR_NAME}, security group: {security_group_id}, instance_params_large: {instance_params_large}")
            print("Skipping t2.large instance launch due to missing key pair or security group.")

    except ClientError as e:
        print(f"Error launching instances: {e}")


# Update the security groups to allow deployment and to run the commands
def update_security_groups(ec2_client, security_group_name):
    try:
        response = ec2_client.describe_security_groups(
                Filters=[{"Name": "group-name", "Values": [security_group_name]}]
            )
        sg = response["SecurityGroups"][0]
        sg_id = sg["GroupId"]
        rules = response['SecurityGroups'][0]['IpPermissions']
        
        ip_permissions = []
        for rule in rules:
            ip_permission = {
                "IpProtocol": rule["IpProtocol"],
                "FromPort": rule["FromPort"],
                "ToPort": rule["ToPort"],
                "IpRanges": rule["IpRanges"]
            }
            ip_permissions.append(ip_permission)
        
        if ip_permissions.__len__() > 0:
            response = ec2_client.revoke_security_group_ingress(GroupId=sg_id, IpPermissions=ip_permissions)

        #Get the gatekeeper IP to allow the HTTP requests
        gatekeeper_ip = get_running_instances("gatekeeper", ec2_client)[0]["PrivateIpAddress"]
        #Get the proxy IP to allow the SSH requests
        proxy_ip = get_running_instances("proxy", ec2_client)[0]["PrivateIpAddress"]
        #Get the trusted machine IP to allow the HTTP requests
        trusted_machine_ip = get_running_instances("trusted_machine", ec2_client)[0]["PrivateIpAddress"]

        final_ip_permissions = []
        if security_group_name == TRUSTED_SECURITY_GROUP_NAME:
            final_ip_permissions = [
                {   # Allow SSH from the everywhere only to allow the deployment and to run the commands
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': "0.0.0.0/0"}]
                },
                {   # Allow HTTP from the gatekeeper
                    'IpProtocol': 'tcp',
                    'FromPort': 8000,
                    'ToPort': 8000,
                    'IpRanges': [{'CidrIp': f'{gatekeeper_ip}/32'}]
                }
            ]
        elif security_group_name == CLUSTER_SECURITY_GROUP_NAME:
            final_ip_permissions = [
                {   # Allow SSH from the everywhere only to allow the deployment and to run the commands
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': "0.0.0.0/0"}]
                },
                {   # Allow pings from the proxy
                    'IpProtocol': 'icmp',
                    'FromPort': -1,
                    'ToPort': -1,
                    'IpRanges': [{'CidrIp': f'{proxy_ip}/32'}]
                },
                {   # Allow HTTP from the trusted machine and proxy
                    'IpProtocol': 'tcp',
                    'FromPort': 8000,
                    'ToPort': 8000,
                    'IpRanges': [{'CidrIp': f'{trusted_machine_ip}/32'}, {'CidrIp': f'{proxy_ip}/32'}]
                }
            ]

        response = ec2_client.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=final_ip_permissions)
        print(f"Security Group ({security_group_name}) updated")
    
    except Exception as e:
        print(f"Erro ao atualizar o Security Group: {e}")

def get_running_instances(tag, ec2_client):
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

def create_instances():
    
    ec2_client = boto3.client('ec2', region_name=REGION)
    
    # Create Key Pair
    key_pair_name = create_key_pair(ec2_client)

    # Create Security Group
    security_group_id = create_security_group(ec2_client, SECURITY_GROUP_NAME)

    # Create Trusted Security Group
    trusted_security_group_id = create_security_group(ec2_client, TRUSTED_SECURITY_GROUP_NAME)

    # Create Cluster Security Group
    cluster_security_group_id = create_security_group(ec2_client, CLUSTER_SECURITY_GROUP_NAME)

    # Launch EC2 Instances and Update the Security Groups IP Permissions
    if key_pair_name and security_group_id and trusted_security_group_id:
        launch_instances(ec2_client, security_group_id, trusted_security_group_id, cluster_security_group_id)
        update_security_groups(ec2_client, TRUSTED_SECURITY_GROUP_NAME)
        update_security_groups(ec2_client, CLUSTER_SECURITY_GROUP_NAME)
        
#create_instances()
        
