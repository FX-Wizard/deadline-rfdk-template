import builtins
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_docdbelastic as docdbelastic
)
from constructs import Construct
from aws_rfdk import deadline


class Deadline_Database(Construct):

    def __init__(self, scope: Construct, id: str, vpc_id: str) -> None:
        super().__init__(scope, id)

        vpc = ec2.Vpc.from_lookup()

        cfn_cluster = docdbelastic.CfnCluster(self, 'DeadlineDatabase',
            admin_user_name='deadline',
            auth_type='SECRET_ARN',
            cluster_name='DeadlineDatabaseCluster',
            shard_capacity=2,
            shard_count=2
        )