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

        # Create IAM user for Deadline Spot Event Plugin Admin
        # deadline_spot_admin_user = iam.User(self, 'DeadlineSpotEventPluginAdmin',
        #     user_name='DeadlineSpotEventPluginAdmin',
        #     managed_policies=[
        #         iam.ManagedPolicy.from_aws_managed_policy_name('AWSThinkboxDeadlineSpotEventPluginAdminPolicy'),
        #         iam.ManagedPolicy.from_aws_managed_policy_name('AWSThinkboxDeadlineResourceTrackerAdminPolicy'),
        #         iam.ManagedPolicy.from_aws_managed_policy_name('IAMFullAccess'),
        #         iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEC2ReadOnlyAccess')
        #     ]
        # )

        # Get render worker security group
        security_groups = []
        for i, sg_id in enumerate(props.security_group_ids):
            sg = ec2.SecurityGroup.from_security_group_id(
                self, f'render_sg_{i}', security_group_id=sg_id)
            security_groups.append(sg)

        userData = ec2.UserData.for_linux()
        userData.add_commands(
            "#!/bin/bash",
            "sudo mkdir -p /mnt/production",
            "fs-0ee858807f35f47e5.efs.ap-southeast-2.amazonaws.com:/ /mnt/production nfs nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport",
            "sudo mount /mnt/production",
            "export DEADLINE_PATH=/opt/Thinkbox/Deadline10/bin",
            "sudo sed -i 's/^ConnectionType=.*/ConnectionType=Remote/' /var/lib/Thinkbox/Deadline10/deadline.ini",
            "sudo sed -i 's/^ProxyRoot=.*/ProxyRoot=renderqueue.deadline.internal:4433/' /var/lib/Thinkbox/Deadline10/deadline.ini",
            "sudo sed -i 's/^ProxyUseSSL=.*/ProxyUseSSL=True/' /var/lib/Thinkbox/Deadline10/deadline.ini",
            "sudo sed -i 's/^ProxySSLCA=.*/ProxySSLCA=/mnt/production/ca.crt/' /var/lib/Thinkbox/Deadline10/deadline.ini",
            "sudo sed -i 's/^ClientSSLAuthentication=.*/ClientSSLAuthentication=NotRequired/' /var/lib/Thinkbox/Deadline10/deadline.ini",
            "sudo sed -i 's/^ProxyRoot0=.*/renderqueue.deadline.internal:4433%/mnt/production/ca.crt/' /var/lib/Thinkbox/Deadline10/deadline.ini",
            "$DEADLINE_PATH/deadlineworker -shutdown",
            "$DEADLINE_PATH/deadlineworker -nogui"
        )

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
                # instance_types=self.instanceListFormatter(fleet['instance_types']),
                instance_types=[ec2.InstanceType('c5a.4xlarge')],
                fleet_instance_role=fleet_instance_role,
                max_capacity=fleet['max_capacity'],
                worker_machine_image=ami,
                track_instances_with_resource_tracker=True,
                user_data=userData
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