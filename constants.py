from pathlib import Path

KEY_PAIR_NAME = 'my-tp3-key-pair'
PRIVATE_KEY_FILE = Path(f'./{KEY_PAIR_NAME}.pem').resolve()

JSON_FILENAME = 'instance_info.json'
LOCAL_INFO_JSON_PATH = Path(f'./{JSON_FILENAME}').resolve()

LARGE_INSTANCE_TYPE = "t2.large"
MICRO_INSTANCE_TYPE = "t2.micro"
DB_CONFIG = {
    "host": "localhost",     # Ou "127.0.0.1"
    "user": "root",          # Usuário do MySQL
    "password": "",          # Senha vazia
    "database": "sakila",    # Nome do banco de dados
}
SECURITY_GROUP_NAME = 'my-tp3-security-group'
TRUSTED_SECURITY_GROUP_NAME = 'trusted-security-group'
GATEKEEPER_IPCONFIG = [
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
            ]
TRUSTED_IPCONFIG = [
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
# LOCAL_FASTAPI_CLUSTER1_PATH = Path('./FastAPI/fastapi-cluster1.py').resolve()
# LOCAL_FASTAPI_CLUSTER2_PATH = Path('./FastAPI/fastapi-cluster2.py').resolve()
# LOCAL_ALB_APP_PATH = Path('./ALB/alb.py').resolve()
REMOTE_APP_PATH = "/home/ubuntu/"  # Remote path for all scripts



AWS_CREDENTIALS_FILE = Path('~/.aws/credentials').expanduser().resolve()  # Local AWS credentials file path
REMOTE_AWS_CREDENTIALS_PATH = "/home/ubuntu/.aws/credentials" 
REGION = "us-east-1"
