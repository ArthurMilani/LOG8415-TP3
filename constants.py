from pathlib import Path

KEY_PAIR_NAME = 'my-tp3-key-pair'
PRIVATE_KEY_FILE = Path(f'./{KEY_PAIR_NAME}.pem').resolve()
SECURITY_GROUP_NAME = 'my-tp3-security-group'

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



# Application script paths
LOCAL_WORKER_PATH = Path('./FastAPI Applications/worker.py').resolve()
LOCAL_MANAGER_PATH = Path('./FastAPI Applications/manager.py').resolve()
LOCAL_PROXY_PATH = Path('./FastAPI Applications/proxy.py').resolve()
# LOCAL_FASTAPI_CLUSTER1_PATH = Path('./FastAPI/fastapi-cluster1.py').resolve()
# LOCAL_FASTAPI_CLUSTER2_PATH = Path('./FastAPI/fastapi-cluster2.py').resolve()
# LOCAL_ALB_APP_PATH = Path('./ALB/alb.py').resolve()
REMOTE_APP_PATH = "/home/ubuntu/"  # Remote path for all scripts



AWS_CREDENTIALS_FILE = Path('~/.aws/credentials').expanduser().resolve()  # Local AWS credentials file path
REMOTE_AWS_CREDENTIALS_PATH = "/home/ubuntu/.aws/credentials" 
REGION = "us-east-1"
