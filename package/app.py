#!/usr/bin/env python3
import os

import aws_cdk as cdk

from .lib.rfdk_deadline_template_stack import RfdkDeadlineTemplateStack, DeadlineStackProps
from .lib.vpc_stack import VpcStack
from .lib.spot_fleet_stack import SpotFleetStack
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
        "Renderfarm-VPC",
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

# Create Spot Fleet Stack
from .lib.spot_fleet_stack import SpotFleetStackProps

spot_fleet_props = SpotFleetStackProps(
    vpc=vpc_stack.vpc if vpc_stack else None,
    vpc_id=config.vpc_id if not vpc_stack else None,
    aws_region=config.aws_region,
    spot_fleet_configs=config.spot_fleet_configs,
    render_queue=deadline_stack.render_queue,
    security_group_ids=[deadline_stack.render_worker_sg.security_group_id],
    create_resource_tracker_role=True
)

spot_fleet_stack = SpotFleetStack(
    app,
    "SpotFleetStack",
    props=spot_fleet_props,
    env=env
)

# Add dependencies
if vpc_stack:
    spot_fleet_stack.add_dependency(vpc_stack)
spot_fleet_stack.add_dependency(deadline_stack)

app.synth()