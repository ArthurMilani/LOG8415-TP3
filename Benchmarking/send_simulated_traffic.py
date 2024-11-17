import asyncio
import aiohttp
import time

async def call_endpoint_http(session, request_num, alb_dns, cluster):
    url = f"http://{alb_dns}:8000/{cluster}"
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

async def run_sim(alb_dns):
    num_requests = 30
    num_requests1 = num_requests // 2
    num_requests2 = num_requests // 2
    print(f"Sending {num_requests1} requests to Cluster1...")
    start_time = time.time()
    

    async with aiohttp.ClientSession() as session:
        tasks = [call_endpoint_http(session, i, alb_dns, "cluster1") for i in range(num_requests1)]
        await asyncio.gather(*tasks)

    end_time = time.time()
    cluster1_total_time = f"{end_time - start_time:.2f}"
    cluter1_avg_time = f"{(end_time - start_time) / num_requests:.4f}"

    print(f"Sending {num_requests2} requests to Cluster2...")
    start_time = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = [call_endpoint_http(session, i, alb_dns, "cluster2") for i in range(num_requests2)]
        await asyncio.gather(*tasks)

    end_time = time.time()
    print(f"\n(CLUSTER 1) Total time taken: {cluster1_total_time} seconds")
    print(f"(CLUSTER 1) Average time per request: {cluter1_avg_time} seconds")

    print(f"\n(CLUSTER 2) Total time taken: {end_time - start_time:.2f} seconds")
    print(f"(CLUSTER 2) Average time per request: {(end_time - start_time) / num_requests:.4f} seconds")
