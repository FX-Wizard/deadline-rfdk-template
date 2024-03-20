#!/usr/bin/env python3
import os

import aws_cdk as cdk

from .lib.rfdk_deadline_template_stack import RfdkDeadlineTemplateStack, DeadlineStackProps

from .config import AppConfig

app = cdk.App()

# Get RFDK configuration options
config: AppConfig = AppConfig()

stack_props = DeadlineStackProps(
    vpc_id=config.vpc_id,
    aws_region=config.aws_region,
    docker_recipes_stage_path=os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'stage'),
    worker_image=config.deadline_client_linux_ami_map
)


RfdkDeadlineTemplateStack(app, "RfdkDeadlineTemplateStack",
    # ID of VPC to deploy into
    props=stack_props,
    
    # If you don't specify 'env', this stack will be environment-agnostic.
    # Account/Region-dependent features and context lookups will not work,
    # but a single synthesized template can be deployed anywhere.

    # Uncomment the next line to specialize this stack for the AWS Account
    # and Region that are implied by the current CLI configuration.

    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=config.aws_region),

    # Uncomment the next line if you know exactly what Account and Region you
    # want to deploy the stack to. */

    # env=cdk.Environment(account='123456789012', region='us-east-1'),

    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
)


app.synth()
