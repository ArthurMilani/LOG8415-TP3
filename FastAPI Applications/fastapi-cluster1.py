from fastapi import FastAPI
import uvicorn
import logging
import requests
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI()

def cpu_task(duration):
    start_time = time.time()
    while time.time() - start_time < duration:
        for _ in range(1000000):
            pass  # Loop de operação inútil para gerar carga na CPU
    print("CPU task completed")

#Get the instance ID with the metadata service
def get_aws_instance_id():
    try:
        token = get_aws_token()
        response = requests.get(
            "http://169.254.169.254/latest/meta-data/instance-id", 
            headers={"X-aws-ec2-metadata-token": token},
            timeout=2
        )
        return response.text

    except requests.RequestException as e:
        logger.error(f"Error fetching instance ID: {e}")
        return "Unable to fetch instance ID"

#Get the token with the metadata service
def get_aws_token():
    try:
        response = requests.put(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=2
        )
        return response.text

    except requests.RequestException as e:
        logger.error(f"Error fetching token: {e}")
        return "Unable to fetch token"


@app.get("/cluster1")
async def root():
    print("hello from cluster 1")
    instance_id = get_aws_instance_id()
    message = f"Cluster 1: Fastest instance number {instance_id} has received the request"
    logger.info(message)
    cpu_task(10)
    return {"message": message}


