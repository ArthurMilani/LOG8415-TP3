import asyncio
import time
import aiohttp
from faker import Faker
import random
import uuid
import requests

names = [] #List to store the names of the users in order to make the read requests
readErrors = [] #Append the errors
writeErrors = [] #Append the errorslock = asyncio.Lock()
lock = asyncio.Lock()

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
            if response_json.get('manager_response') is not None and response_json.get('replication_status') is not None:
                print(f"""      
-----------------------------------------
WRITE QUERY: {query}
Request {request_num}: Status Code: {status_code}
Response: {response_json}
-----------------------------------------
""")
            else:
                raise Exception("Something went wrong with the write request")
            return status_code, response_json
    except Exception as e:
        print(f"Request {request_num}: Failed - {str(e)}")
        async with lock:
            writeErrors.append(str(e))
        return None, str(e)


#Read requests for benchmarking, calling the gatekeeper
async def call_endpoint_read_http(session, request_num, gatekeeper_dns, read_type):

    query = search_random_users()
#TODO: Adpatar para imprimir mais de um usuário
    url = f"http://{gatekeeper_dns}:8000/read?method={read_type}&query={query}"
    headers = {'content-type': 'application/json'}
    try:
        async with session.get(url, headers=headers) as response:
            status_code = response.status
            response_json = await response.json()
            output = response_json['result']['stdout']
            if status_code == 200 and output != "":
                lines = output.split('\n')
                print(f"-----------------------------------------\nREAD QUERY: {query}\nRequest {request_num}: Status Code: {status_code}")
                for line in lines[1:-1]:
                    values = line.split('\t')
                    id, name, age = values
                    print(f"ID: {id}\nName: {name}\nAge: {age}")
                print("-----------------------------------------")

            elif status_code == 200 and output == "":
                print(f"""
-----------------------------------------
READ QUERY: {query}
Request {request_num}: Status Code: {status_code}
USER NOT INSERTED YET
-----------------------------------------
""")

            return status_code, response_json
    except Exception as e:
        print(f"Request {request_num}: Failed - {str(e)}")
        async with lock:
            readErrors.append(str(e))
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
    num_requests = 1000
    read_types = ["direct_hit", "random", "customized"]

    create_user_table(gatekeeper_dns)
    
    for read_type in read_types:
        print("")
        print(f"Starting {read_type} requests...")
        print("")
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(num_requests):
              
                tasks.append(call_endpoint_write_http(session, i, gatekeeper_dns))
                tasks.append(call_endpoint_read_http(session, i, gatekeeper_dns, read_type))

            await asyncio.gather(*tasks)
        end_time = time.time()

        print(f"\nTotal time taken for {read_type} requests: {end_time - start_time:.2f} seconds")
        print(f"Success Write Requests Rate: {num_requests - len(writeErrors)}/{num_requests}")
        print(f"Success Read Requests Rate: {num_requests - len(readErrors)}/{num_requests}")
        readErrors.clear()
        writeErrors.clear()
        
        print("Press enter to continue the benchmarking...")
        input()



# #TODO: Remove
# gatekeeper_dns = "23.22.133.132"
# asyncio.run(run_sim(gatekeeper_dns))