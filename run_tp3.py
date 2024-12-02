from Benchmarking.send_simulated_traffic import run_sim
from Infrastructure.create_instances import create_instances
from Infrastructure.deploy_files import deploy_files
from Infrastructure.deploy_files import update_ssh_rules
from Infrastructure.deploy_files import perform_sysbench_benchmarks
from Infrastructure.deploy_files import set_ip_table_rules

import asyncio

async def main():
    print("--------------------------------------------")
    print("Creating instances...")
    print("--------------------------------------------")
    create_instances()
    print("--------------------------------------------")
    print("Deploying files...")
    print("--------------------------------------------")
    gatekeeper_dns, instances, update_ssh_data = deploy_files()
    print("Deployment complete. To start sysbench benchmarks, press Enter.")
    input()
    print("--------------------------------------------")
    print("Running sysbench benchmarks...")
    print("--------------------------------------------")
    #perform_sysbench_benchmarks(instances)
    print("--------------------------------------------")
    print("Updating SSH and IP-Table rules...")
    print("--------------------------------------------")
    #set_ip_table_rules()
    update_ssh_rules(update_ssh_data[0], update_ssh_data[1], update_ssh_data[2], update_ssh_data[3])
    print("Finished deploying files. To start the cluster benchmarking, press Enter.")
    input()
    print("--------------------------------------------")
    print("Running benchmarking...")
    print("--------------------------------------------")
    await run_sim(gatekeeper_dns)


if __name__ == "__main__":
    asyncio.run(main())