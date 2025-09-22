import aws_cdk as cdk
import aws_rfdk as rfdk
from dataclasses import dataclass
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_route53 as route53,
    aws_elasticloadbalancingv2 as elb2
)
from constructs import Construct
from aws_rfdk import deadline, SessionManagerHelper
from typing import Mapping, Optional


@dataclass
class DeadlineStackProps(cdk.StackProps):
    vpc: Optional[ec2.IVpc] = None
    vpc_id: Optional[str] = None
    aws_region: str = None
    renderqueue_name: str = None
    zone_name: str = None
    deadline_version: str = None
    use_traffic_encryption: bool = None
    docker_recipes_stage_path: str = None
    spot_fleet_configs: dict = None


class RfdkDeadlineTemplateStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, props: DeadlineStackProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Use VPC object directly if provided, otherwise lookup by ID
        if props.vpc:
            vpc = props.vpc
        else:
            vpc = ec2.Vpc.from_lookup(
                self, 'Deadline-VPC',
                vpc_id=props.vpc_id
            )
        
        #
        # DNS and SSL
        #
        dns_zone = route53.PrivateHostedZone(self, 'DeadlineDNSPrivateZone',
            vpc=vpc,
            zone_name=props.zone_name
        )

        # Generate a root CA and then use it to sign another identity certificate
        ca_cert = rfdk.X509CertificatePem(self, 'RootCA',
            subject=rfdk.DistinguishedName(cn='DeadlineRootCA')
        )
        cdk.Tags.of(ca_cert).add('Purpose', 'RootCA')

        server_cert = rfdk.X509CertificatePem(self, 'RQCert',
            subject=rfdk.DistinguishedName(
                cn=f'{props.renderqueue_name}.{props.zone_name}',
                o='RFDK-Deadline',
                ou='RenderQueueExternal',
            ),
            signing_certificate=ca_cert
        )
        cdk.Tags.of(ca_cert).add('Purpose', 'RenderQueueCertificate')

        #
        # Deadline Repository
        #
        version = deadline.VersionQuery(self, 'Version',
            version=props.deadline_version,
        )

        # Fetch the Deadline container images for the specified Deadline version
        images = deadline.ThinkboxDockerImages(self, 'Images',
            version=version,
            # The ThinkboxDockerImages will install Deadline onto one or more EC2 instances.
            # By downloading or using the Deadline software, you agree to the AWS Customer Agreement (https://aws.amazon.com/agreement/)
            # and AWS Intellectual Property License (https://aws.amazon.com/legal/aws-ip-license-terms/). You acknowledge that Deadline
            # is AWS Content as defined in those Agreements.
            # Please set the user_aws_customer_agreement_and_ip_license_acceptance property to
            # USER_ACCEPTS_AWS_CUSTOMER_AGREEMENT_AND_IP_LICENSE to signify your acceptance of these terms.
            user_aws_customer_agreement_and_ip_license_acceptance=
                deadline.AwsCustomerAgreementAndIpLicenseAcceptance.USER_ACCEPTS_AWS_CUSTOMER_AGREEMENT_AND_IP_LICENSE
        )

        repository = deadline.Repository(self, 'Repository',
            vpc=vpc,
            version=version,
            repository_installation_timeout=cdk.Duration.minutes(20),
            removal_policy=deadline.RepositoryRemovalPolicies(
                database=cdk.RemovalPolicy.DESTROY,
                filesystem=cdk.RemovalPolicy.DESTROY
            ),
            # Use private subnets
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
        )

        if props.use_traffic_encryption:
            traffic_encryption=deadline.RenderQueueTrafficEncryptionProps(
                external_tls=deadline.RenderQueueExternalTLSProps(
                    rfdk_certificate=server_cert,
                ),
                internal_protocol=elb2.ApplicationProtocol.HTTPS
            )
        else:
            traffic_encryption=deadline.RenderQueueTrafficEncryptionProps(
                external_tls=deadline.RenderQueueExternalTLSProps(
                    enabled=False
                ),
                internal_protocol=elb2.ApplicationProtocol.HTTPS
            )

        # Use the container images to create a RenderQueue
        render_queue = deadline.RenderQueue(self, 'RenderQueue',
            vpc=vpc,
            repository=repository,
            version=version,
            images=images.for_render_queue(),
            deletion_protection=False,
            hostname=deadline.RenderQueueHostNameProps(
                hostname=props.renderqueue_name,
                zone=dns_zone,
            ),
            traffic_encryption=traffic_encryption,
            # Use private subnets
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
        )
        # Allow terminal connection to render queue via Session Manager
        SessionManagerHelper.grant_permissions_to(render_queue.asg)

        render_queue.connections.allow_default_port_from(ec2.Peer.ipv4(vpc.vpc_cidr_block))

        # Security group for render workers
        render_worker_sg = ec2.SecurityGroup(self, 'Deadline-Render-Worker-SG',
            vpc=vpc, 
            security_group_name='Deadline-Render-Worker-SG',
            allow_all_outbound=True
        )

        # Expose for other stacks
        self.render_queue = render_queue
        self.render_worker_sg = render_worker_sg
