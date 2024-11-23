import asyncio
import aiohttp
import time
from faker import Faker
import random
import uuid
import requests

names = []
async def call_endpoint_write_http(session, request_num, proxy_dns):
 
    url = f"http://{proxy_dns}:8000/write"
    headers = {'Content-Type': 'application/json'}
    json = {"query": create_user()}
    try:
        async with session.post(url, headers=headers, json=json) as response:
            status_code = response.status
            response_json = await response.json()
            print(url)
            print(f"Request {request_num}: Status Code: {status_code}, Response: {response_json}")
            return status_code, response_json
    except Exception as e:
        print(f"Request {request_num}: Failed - {str(e)}")
        return None, str(e)


async def call_endpoint_read_http(session, request_num, proxy_dns, read_type):

    query = search_random_users()

    url = f"http://{proxy_dns}:8000/read?method={read_type}&query={query}" #TODO: Change this to the correct URL
    headers = {'content-type': 'application/json'}
    try:
        async with session.get(url, headers=headers) as response:
            status_code = response.status
            response_json = await response.json()
            print(url)
            print(f"Request {request_num}: Status Code: {status_code}, Response: {response_json}")
            return status_code, response_json
    except Exception as e:
        print(f"Request {request_num}: Failed - {str(e)}")
        return None, str(e)
    

def create_user_table(proxy_dns):
    url = f"http://{proxy_dns}:8000/write"
    query = "USE sakila; CREATE TABLE IF NOT EXISTS users (id CHAR(36) PRIMARY KEY, name VARCHAR(100) NOT NULL, age INT NOT NULL);"
    try:
        response = requests.post(url, json={"query": query})
    
        return response.json()
    except requests.RequestException as e:
        print(f"Error sending request to {proxy_dns}: {e}")
        return None


def create_user():
    u_uid = uuid.uuid4()
    faker = Faker("pt_BR")
    name = faker.name()
    names.append(name)
    age = random.randint(18, 60)
    query = f"USE sakila; INSERT INTO users (id, name, age) VALUES (\"{u_uid}\",\"{name}\", {age});"
    return query

def search_random_users():
    name = random.choice(names)
    query = f"USE sakila; SELECT * FROM users WHERE name = \"{name}\";"
    return query


async def run_sim(proxy_dns):
    num_requests = 50
    read_types = ["direct_hit", "random", "customized"]

    create_user_table(proxy_dns)
    
    for read_type in read_types:
        print(f"Sending {num_requests} {read_type} requests...")
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(num_requests):
              
                tasks.append(call_endpoint_write_http(session, i, proxy_dns))
                tasks.append(call_endpoint_read_http(session, i, proxy_dns, read_type))

            await asyncio.gather(*tasks)
        end_time = time.time()

        print(f"Total time taken: {end_time - start_time:.2f} seconds")
        print(f"Average time per request: {(end_time - start_time) / num_requests:.4f} seconds\n")


proxy_dns = "35.175.198.75"
asyncio.run(run_sim(proxy_dns))
