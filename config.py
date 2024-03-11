import os


class AppConfig:
    """
    
    """
    def __init__(self) -> None:

        self.aws_region:str = os.getenv('CDK_DEFAULT_REGION')
        self.vpc_id: str = os.getenv('CDK_DEFAULT_VPC')

        # Note: Deadline's Resource Tracker only supports a single Deadline Repository per AWS account.
        self.create_resource_tracker_role: bool = True


config: AppConfig = AppConfig()