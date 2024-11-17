from pathlib import Path
import sys
import boto3
from botocore.exceptions import ClientError
import os

parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

from constants import KEY_PAIR_NAME, LARGE_INSTANCE_TYPE, MICRO_INSTANCE_TYPE, REGION, SECURITY_GROUP_NAME

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

# Create Key Pair
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

# Create Security Group
def create_security_group(ec2_client, security_group_name):
    try:
        response_security_group = ec2_client.create_security_group(
            GroupName=security_group_name, Description="Security group for TP1 EC2 instance"
        )
        security_group_id = response_security_group["GroupId"]
        print(f"Security Group ({security_group_id}) created: {security_group_id}")

        # Authorize Security Group Ingress
        ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],  # Allow SSH from anywhere
                },
                {
                    "IpProtocol": "tcp",
                    "FromPort": 8000,
                    "ToPort": 8000,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],  # Allow traffic on port 8000
                },
                {
                    "IpProtocol": 'icmp',  # Protocolo ICMP
                    "FromPort": -1,       # ICMP não usa portas, -1 é padrão
                    "ToPort": -1,
                    "IpRanges": [{'CidrIp': '0.0.0.0/0'}]  # Permite de qualquer lugar
                },
            ],
        )
        return security_group_id
    except ClientError as e:
        if "InvalidGroup.Duplicate" in str(e):
            return get_existing_security_group(ec2_client, security_group_name)
        else:
            print(f"Error creating security group: {e}")
            security_group_id = None
            
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

def launch_instances(ec2_client, security_group_id):

    # Check the number of running instances
    if count_running_instances(ec2_client) >= 4:
        print("Skipping instance launch: already 3 instances are running.")
        return
    
    # Parameters for EC2 Instances
    instance_params_micro = {
        "ImageId": "ami-0e86e20dae9224db8",
        "InstanceType": MICRO_INSTANCE_TYPE,
        "MinCount": 2,
        "MaxCount": 2,
        "KeyName": KEY_PAIR_NAME,
        "TagSpecifications": [{'ResourceType': 'instance', 'Tags': [{'Key': 'Role', 'Value': 'worker'}]}],
        "SecurityGroupIds": [security_group_id],
        "BlockDeviceMappings": [
            {"DeviceName": "/dev/xvda", "Ebs": {"VolumeSize": 8, "VolumeType": "gp3"}}
        ],
        "Monitoring": {"Enabled": True}, 
    }

    instance_params_large = {
        "ImageId": "ami-0e86e20dae9224db8",
        "InstanceType": LARGE_INSTANCE_TYPE,
        "MinCount": 1,
        "MaxCount": 1,
        "KeyName": KEY_PAIR_NAME,
        "TagSpecifications": [{'ResourceType': 'instance', 'Tags': [{'Key': 'Role', 'Value': 'proxy'}]}],
        "SecurityGroupIds": [security_group_id],
        "BlockDeviceMappings": [
            {"DeviceName": "/dev/xvda", "Ebs": {"VolumeSize": 8, "VolumeType": "gp3"}}
        ],
        "Monitoring": {"Enabled": True}, 
    }

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

        # Launch t2.large instances
        if instance_params_large["KeyName"] and instance_params_large["SecurityGroupIds"]:
            response_large = ec2_client.run_instances(**instance_params_large)
            instance_ids_large = [instance["InstanceId"] for instance in response_large["Instances"]]
            print(f"Launched EC2 t2.large instances with IDs: {instance_ids_large}")

            # Wait for the t2.large instances to be in the 'running' state
            print("Waiting for t2.large instances to be running...")
            waiter.wait(InstanceIds=instance_ids_large)
            print("t2.large instances are now running.")
        else:
            print(f"Key pair: {KEY_PAIR_NAME}, security group: {security_group_id}, instance_params_large: {instance_params_large}")
            print("Skipping t2.large instance launch due to missing key pair or security group.")

    except ClientError as e:
        print(f"Error launching instances: {e}")
        
def create_instances():
    
    ec2_client = boto3.client('ec2', region_name=REGION)
    
    # Create Key Pair
    key_pair_name = create_key_pair(ec2_client)

    # Create Security Group
    security_group_id = create_security_group(ec2_client, SECURITY_GROUP_NAME)

    # Launch EC2 Instances
    if key_pair_name and security_group_id:
        launch_instances(ec2_client, security_group_id)
        
create_instances()
        
