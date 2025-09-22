import aws_cdk as cdk
import aws_rfdk as rfdk
from dataclasses import dataclass
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
)
from constructs import Construct
from aws_rfdk import deadline
from aws_rfdk.deadline import RenderQueue, SpotEventPluginFleet, ConfigureSpotEventPlugin, SpotEventPluginSettings
from typing import Mapping, Optional


@dataclass
class SpotFleetStackProps(cdk.StackProps):
    vpc: Optional[ec2.IVpc] = None
    vpc_id: Optional[str] = None
    aws_region: str = None
    spot_fleet_configs: dict = None
    render_queue: RenderQueue = None
    security_group_ids: list = None
    create_resource_tracker_role: Optional[bool] = None
    fleet_instance_role: Optional[iam.Role] = None


class SpotFleetStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, props: SpotFleetStackProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create IAM role needed for Resource Tracker
        if props.create_resource_tracker_role:
            iam.Role(self, 'ResourceTrackerRole',
                assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
                managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name(
                    'AWSThinkboxDeadlineResourceTrackerAccessPolicy')],
                role_name='DeadlineResourceTrackerAccessRole'
            )

        # Create IAM role for spot fleet worker
        fleet_instance_role = iam.Role(self, 'DeadlineWorkerEC2Role',
            role_name='DeadlineWorkerEC2Role',
            assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name('AWSThinkboxDeadlineSpotEventPluginWorkerPolicy'),
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore')
            ],
        )

        # Get render worker security group
        security_groups = []
        for i, sg_id in enumerate(props.security_group_ids):
            sg = ec2.SecurityGroup.from_security_group_id(
                self, f'render_sg_{i}', security_group_id=sg_id)
            security_groups.append(sg)

        spot_fleets = []

        for i, fleet in props.spot_fleet_configs.items():
            if fleet["is_linux"]:
                ami = ec2.MachineImage.generic_linux(fleet['worker_image'])
            else:
                ami = ec2.MachineImage.generic_windows(fleet['worker_image'])
            spot_fleet_config = deadline.SpotEventPluginFleet(self,
                fleet['name'],
                vpc=props.vpc,
                render_queue=props.render_queue,
                deadline_groups=fleet['deadline_groups'],
                deadline_pools=fleet['deadline_pools'],
                security_groups=security_groups,
                instance_types=self.instanceListFormatter(fleet['instance_types']),
                fleet_instance_role=fleet_instance_role,
                max_capacity=fleet['max_capacity'],
                worker_machine_image=ami,
            )
            if fleet['tags']:
                for key, value in fleet['tags'].items():
                    cdk.Tags.of(spot_fleet_config).add(key, value)
            spot_fleets.append(spot_fleet_config)

        ConfigureSpotEventPlugin(self, 'SpotEventPluginConfig',
            vpc=props.vpc,
            render_queue=props.render_queue,
            spot_fleets=spot_fleets,
            configuration=SpotEventPluginSettings(
                enable_resource_tracker=True
            )
        )

    def instanceListFormatter(self, instance_list: list) -> list:
        """
        Formats a list of instance names into a list of ec2.InstanceType
        """
        instance_type_format_list = []

        for name in instance_list:
            instance_type_format= ec2.InstanceType(name)
            instance_type_format_list.append(instance_type_format)

        return instance_type_format_list