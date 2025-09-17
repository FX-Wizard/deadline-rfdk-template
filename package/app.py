#!/usr/bin/env python3
import os

import aws_cdk as cdk

from .lib.rfdk_deadline_template_stack import RfdkDeadlineTemplateStack, DeadlineStackProps
from .lib.vpc_stack import VpcStack
from .config import AppConfig

app = cdk.App()

# Get RFDK configuration options
config: AppConfig = AppConfig()

# Create environment for the stacks
env = cdk.Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT'),
    region=config.aws_region
)

# Create VPC Stack only if vpc_id is not provided
vpc_stack = None
if not config.vpc_id:
    vpc_stack = VpcStack(
        app,
        stack_name="Renderfarm-VPC",
        env=env
    )

# Create Deadline Stack with appropriate VPC reference
if vpc_stack:
    # Pass VPC object directly
    stack_props = DeadlineStackProps(
        vpc=vpc_stack.vpc,
        aws_region=config.aws_region,
        renderqueue_name=config.renderqueue_name,
        zone_name=config.zone_name,
        deadline_version=config.deadline_version,
        use_traffic_encryption=config.use_traffic_encryption,
        create_resource_tracker_role=config.create_resource_tracker_role,
        docker_recipes_stage_path=os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'stage'),
        spot_fleet_configs=config.spot_fleet_configs,
    )
else:
    # Use existing VPC ID
    stack_props = DeadlineStackProps(
        vpc_id=config.vpc_id,
        aws_region=config.aws_region,
        renderqueue_name=config.renderqueue_name,
        zone_name=config.zone_name,
        deadline_version=config.deadline_version,
        use_traffic_encryption=config.use_traffic_encryption,
        create_resource_tracker_role=config.create_resource_tracker_role,
        docker_recipes_stage_path=os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'stage'),
        spot_fleet_configs=config.spot_fleet_configs,
    )

deadline_stack = RfdkDeadlineTemplateStack(
    app,
    "RfdkDeadlineTemplateStack",
    props=stack_props,
    env=env
)

# Add dependency only if VPC stack was created
if vpc_stack:
    deadline_stack.add_dependency(vpc_stack)

app.synth()