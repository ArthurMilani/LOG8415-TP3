import asyncio
import aiohttp
from faker import Faker
import random
import uuid
import requests

names = [] #List to store the names of the users in order to make the read requests

#Write requests for benchmarking, calling the gatekeeper
async def call_endpoint_write_http(session, request_num, gatekeeper_dns):
 
    url = f"http://{gatekeeper_dns}:8000/write"
    headers = {'Content-Type': 'application/json'}
    query = create_user()
    json = {"query": query}
    try:
        async with session.post(url, headers=headers, json=json) as response:
            status_code = response.status
            response_json = await response.json()
            if status_code == 200:
                print(f"""      
-----------------------------------------
WRITE QUERY: {query}
Request {request_num}: Status Code: {status_code}
Response: {response_json}
-----------------------------------------
""")
            return status_code, response_json
    except Exception as e:
        print(f"Request {request_num}: Failed - {str(e)}")
        return None, str(e)


#Read requests for benchmarking, calling the gatekeeper
async def call_endpoint_read_http(session, request_num, gatekeeper_dns, read_type):

    query = search_random_users()

    url = f"http://{gatekeeper_dns}:8000/read?method={read_type}&query={query}"
    headers = {'content-type': 'application/json'}
    try:
        async with session.get(url, headers=headers) as response:
            status_code = response.status
            response_json = await response.json()
            output = response_json['result']['stdout']
            if status_code == 200 and output != "":
                lines = output.split('\n')
                values = lines[1].split('\t')
                id, name, age = values
                print(f"""                      
-----------------------------------------
READ QUERY: {query}
Request {request_num}: Status Code: {status_code}
ID: {id}
Name: {name}
Age: {age}
-----------------------------------------
""")
            return status_code, response_json
    except Exception as e:
        print(f"Request {request_num}: Failed - {str(e)}")
        return None, str(e)
    
#Create a table for the benchmarking
def create_user_table(gatekeeper_dns):
    url = f"http://{gatekeeper_dns}:8000/write"
    query = "CREATE TABLE IF NOT EXISTS users (id CHAR(36) PRIMARY KEY, name VARCHAR(100) NOT NULL, age INT NOT NULL)"
    try:
        response = requests.post(url, json={"query": query})
        return response.json()
    except requests.RequestException as e:
        print(f"Error sending request to {gatekeeper_dns}: {e}")
        return None

#Create random users for the benchmarking
def create_user():
    u_uid = uuid.uuid4()
    faker = Faker("pt_BR")
    name = faker.name()
    names.append(name)
    age = random.randint(18, 60)
    query = f"INSERT INTO users (id, name, age) VALUES (\"{u_uid}\",\"{name}\", {age})"
    return query

#Search for random users for the benchmarking
def search_random_users():
    name = random.choice(names)
    query = f"SELECT * FROM users WHERE name = \"{name}\""
    return query

#Main function to run the benchmarking
async def run_sim(gatekeeper_dns):
    num_requests = 10
    read_types = ["direct_hit", "random", "customized"]

    create_user_table(gatekeeper_dns)
    
    for read_type in read_types:
        print("")
        print(f"Starting {read_type} requests...")
        print("")
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(num_requests):
              
                tasks.append(call_endpoint_write_http(session, i, gatekeeper_dns))
                tasks.append(call_endpoint_read_http(session, i, gatekeeper_dns, read_type))

            await asyncio.gather(*tasks)
            

#TODO: Remove
# gatekeeper_dns = "98.84.176.48"
# asyncio.run(run_sim(gatekeeper_dns))