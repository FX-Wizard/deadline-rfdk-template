import os
from typing import Mapping


class AppConfig:
    """
    
    """
    def __init__(self) -> None:

        self.aws_region:str = os.getenv('CDK_DEFAULT_REGION')
        self.vpc_id: str = os.getenv('CDK_DEFAULT_VPC')

        # Worker AMI
        self.deadline_client_linux_ami_map: Mapping[str, str] = {'ap-southeast-2': 'ami-04b0896de2d480709'}

        # Note: Deadline's Resource Tracker only supports a single Deadline Repository per AWS account.
        self.create_resource_tracker_role: bool = True



config: AppConfig = AppConfig()