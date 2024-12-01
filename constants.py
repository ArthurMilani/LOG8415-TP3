from pathlib import Path

KEY_PAIR_NAME = 'my-tp3-key-pair'
PRIVATE_KEY_FILE = Path(f'./{KEY_PAIR_NAME}.pem').resolve()

JSON_FILENAME = 'instance_info.json'
LOCAL_INFO_JSON_PATH = Path(f'./{JSON_FILENAME}').resolve()

LARGE_INSTANCE_TYPE = "t2.large"
MICRO_INSTANCE_TYPE = "t2.micro"
DB_CONFIG = {
    "host": "localhost",     
    "user": "root",          
    "password": "",          
    "database": "sakila",    
}
SECURITY_GROUP_NAME = 'gatekeeper-security-group'
TRUSTED_SECURITY_GROUP_NAME = 'trusted-security-group'
CLUSTER_SECURITY_GROUP_NAME = 'cluster-security-group'
GATEKEEPER_IPCONFIG = [
                {
                    "IpProtocol": "tcp",   # Allow SSH traffic
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}], 
                },
                {
                    "IpProtocol": "tcp",   # Allow traffic on port 8000
                    "FromPort": 8000,
                    "ToPort": 8000,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],  
                },
                {
                    "IpProtocol": 'icmp',  # ICMP Protocol
                    "FromPort": -1,       
                    "ToPort": -1,
                    "IpRanges": [{'CidrIp': '0.0.0.0/0'}] 
                },
            ]

CLUSTER_IPCONFIG = [
                {
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],  # Allow SSH from anywhere
                }
] #TODO

MICRO_INSTANCE = {
        "ImageId": "ami-0e86e20dae9224db8",
        "InstanceType": MICRO_INSTANCE_TYPE,
        "MinCount": 2,
        "MaxCount": 2,
        "KeyName": KEY_PAIR_NAME,
        "TagSpecifications": [{'ResourceType': 'instance', 'Tags': [{'Key': 'Role', 'Value': 'worker'}]}],
        "BlockDeviceMappings": [
            {"DeviceName": "/dev/xvda", "Ebs": {"VolumeSize": 8, "VolumeType": "gp3"}}
        ],
        "Monitoring": {"Enabled": True}, 
    }

LARGE_INSTANCE = {
        "ImageId": "ami-0e86e20dae9224db8",
        "InstanceType": LARGE_INSTANCE_TYPE,
        "MinCount": 1,
        "MaxCount": 1,
        "KeyName": KEY_PAIR_NAME,
        "TagSpecifications": [{'ResourceType': 'instance', 'Tags': [{'Key': 'Role', 'Value': 'proxy'}]}],
        "BlockDeviceMappings": [
            {"DeviceName": "/dev/xvda", "Ebs": {"VolumeSize": 8, "VolumeType": "gp3"}}
        ],
        "Monitoring": {"Enabled": True}, 
    }

# Application script paths
LOCAL_WORKER_PATH = Path('./FastAPI Applications/worker.py').resolve()
LOCAL_MANAGER_PATH = Path('./FastAPI Applications/manager.py').resolve()
LOCAL_PROXY_PATH = Path('./FastAPI Applications/proxy.py').resolve()
LOCAL_TRUSTED_PATH = Path('./FastAPI Applications/trusted_machine.py').resolve()
LOCAL_GATEKEEPER_PATH = Path('./FastAPI Applications/gatekeeper.py').resolve()
REMOTE_APP_PATH = "/home/ubuntu/"  # Remote path for all scripts

AWS_CREDENTIALS_FILE = Path('~/.aws/credentials').expanduser().resolve()  # Local AWS credentials file path
REMOTE_AWS_CREDENTIALS_PATH = "/home/ubuntu/.aws/credentials" 
REGION = "us-east-1"
