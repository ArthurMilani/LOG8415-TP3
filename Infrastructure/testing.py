from pathlib import Path
import sys
import boto3
import paramiko
import os
from scp import SCPClient

parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

from constants import REGION

def get_running_instances(ec2_client):
    filters = [{'Name': 'instance-state-name', 'Values': ['running']}]
    response = ec2_client.describe_instances(Filters=filters)
    instances_info = []

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instances_info.append({
                'InstanceId': instance['InstanceId'],
                'InstanceType': instance['InstanceType'],
                'PublicDnsName': instance['PublicDnsName'],
                'Tags': instance['Tags']
            })
    print(instances_info)


ec2 = boto3.client('ec2', region_name=REGION)
get_running_instances(ec2_client=ec2)