import os
from typing import Mapping


class AppConfig:
    """
    Configure RFDK deployment options here
    """
    def __init__(self) -> None:

        # CDK settings
        self.aws_region:str = os.getenv('CDK_DEFAULT_REGION')
        self.vpc_id: str = os.getenv('CDK_DEFAULT_VPC')

        # DNS settings
        self.renderqueue_name: str = 'renderqueue'
        self.zone_name: str = 'deadline.internal'

        # Deadline settings
        self.deadline_version: str = '10.3.1'
        self.use_traffic_encryption: bool = True

        # Worker AMI
        self.deadline_client_linux_ami_map: Mapping[str, str] = {self.aws_region: 'TODO: ADD THE ID OF YOUR AMI HERE'}

        # Deadline's Resource Tracker only supports a single Deadline Repository per AWS account.
        # Set to False if there is an existing Deadline Repository in the account.
        self.create_resource_tracker_role: bool = True

        instance_types: dict = {
            'highMemory': ['m5.12xlarge', 'm5a.12xlarge', 'm6i.12xlarge', 'm6a.12xlarge'],
            'highCpu': ['c5.12xlarge', 'c6i.12xlarge', 'c5a.12xlarge', 'c6a.12xlarge'],
            'medium': ['c5.4xlarge', 'c6i.4xlarge', 'c5a.4xlarge', 'c6a.4xlarge'],
            'small': ['c5.large', 'c6i.large', 'c5a.large', 'c6a.large'],
            'gpu': ['g5.2xlarge', 'g4dn.2xlarge'],
        }

        self.spot_fleet_configs: dict = {
            'blender': {
                'name': 'blender',
                'is_linux': True,
                'deadline_groups': ['blender-cloud'],
                'deadline_pools': ['blender'],
                'instance_types': instance_types['small'],
                'worker_image': self.deadline_client_linux_ami_map,
                'max_capacity': 5,
            }
        }

config: AppConfig = AppConfig()