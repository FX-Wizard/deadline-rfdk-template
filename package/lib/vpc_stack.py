import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
)
from constructs import Construct


class VpcStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Use standard VPC construct - it handles AZ discovery automatically
        self.vpc = ec2.Vpc(
            self,
            "Render-Farm-VPC",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=99,  # Use all available AZs
            nat_gateways=1,  # Only 1 NAT gateway for cost efficiency
            subnet_configuration=[
                # Private subnets in all AZs
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=20,
                ),
                # Public subnets in all AZs (CDK handles this properly)
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
            ],
        )

        # Export the VPC ID as a stack output
        self.vpc_id_output = cdk.CfnOutput(
            self,
            "VpcId",
            value=self.vpc.vpc_id,
            description="VPC ID",
            export_name="VpcId",
        )

    @property
    def vpc_id(self) -> str:
        return self.vpc_id_output.value