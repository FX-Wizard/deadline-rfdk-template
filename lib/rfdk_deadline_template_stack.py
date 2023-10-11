import os
import aws_cdk as cdk
import aws_rfdk as rfdk
from aws_cdk import (
    # Duration,
    Stack,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_iam as iam,
    aws_route53 as route53,
    aws_elasticloadbalancingv2 as elb2
)
from constructs import Construct
from aws_rfdk import deadline, SessionManagerHelper

# Add details here
HOST = 'deadline'
ZONE_NAME = 'template.local'

class RfdkDeadlineTemplateStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, vpc_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        if vpc_id:
            vpc = ec2.Vpc.from_lookup(
                self, 'Deadline-VPC', vpc_id=vpc_id)
        else:
            vpc = ec2.Vpc(self, 'Render-Farm-VPC',
                cidr='172.16.0.0/16',
                max_azs=True,
                subnet_configuration=[
                    ec2.SubnetConfiguration(
                        name='Render-Subnet',
                        cidrMask=20,
                        subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                    )
                ],
                #nat_gateways = 1, # uncomment if you want the render farm to have internet access
            )
        
        #
        # DNS and SSL
        #

        dns_zone = route53.PrivateHostedZone(self, 'DeadlineDNSPrivateZone',
            vpc=vpc,
            zone_name=ZONE_NAME
        )

        # Generate a root CA and then use it to sign another identity certificate
        ca_cert = rfdk.X509CertificatePem(self, 'RootCA',
            subject=rfdk.DistinguishedName(cn='DeadlineRootCA')
        )

        server_cert = rfdk.X509CertificatePem(self, 'RQCert',
            subject=rfdk.DistinguishedName(
                cn=f'{HOST}.{ZONE_NAME}',
                o='RFDK-Deadline',
                ou='RenderQueueExternal',
            ),
            signing_certificate=ca_cert
        )

        # Convert the identity certificate PEM into PKCS#12
        rfdk.X509CertificatePkcs12(self, 'DeadlinePkcs',
            source_certificate=server_cert
        )

        # Import the identity certificate into ACM
        rfdk.ImportedAcmCertificate(self, 'DeadlineAcmCert2',
            cert=server_cert.cert,
            cert_chain=server_cert.cert_chain,
            key=server_cert.key,
            passphrase=server_cert.passphrase,
        )

        #
        # Deadline Repository
        #

        # Specify Deadline Version (in this example we pin to the latest 10.2.0.x)
        version = deadline.VersionQuery(self, 'Version',
            version="10.3.0",
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
            removal_policy=deadline.RepositoryRemovalPolicies(
                database=cdk.RemovalPolicy.DESTROY,
                filesystem=cdk.RemovalPolicy.DESTROY
            )
        )

        # Use the container images to create a RenderQueue
        render_queue = deadline.RenderQueue(self, 'RenderQueue',
            vpc=vpc,
            repository=repository,
            version=version,
            images=images.for_render_queue(),
            deletion_protection=False,
            hostname=deadline.RenderQueueHostNameProps(
                hostname=HOST,
                zone=dns_zone,
            ),
            traffic_encryption=deadline.RenderQueueTrafficEncryptionProps(
                external_tls=deadline.RenderQueueExternalTLSProps(
                    rfdk_certificate=server_cert,
                ),
                internal_protocol=elb2.ApplicationProtocol.HTTPS
            )
            # Uncomment the below to Disable SSL/TLS
            # traffic_encryption=deadline.RenderQueueTrafficEncryptionProps(
            #     external_tls=deadline.RenderQueueExternalTLSProps(
            #         enabled=False
            #     ),
            #     internal_protocol=elb2.ApplicationProtocol.HTTPS
            # ),
        )
        # Allow terminal connection to render queue via Session Manager
        SessionManagerHelper.grant_permissions_to(render_queue.asg)

        render_queue.connections.allow_default_port_from(ec2.Peer.ipv4(vpc.vpc_cidr_block))

        #
        # Spot render fleet
        #

        if not iam.Role.from_role_name(self, 'role-exists-check', role_name='DeadlineResourceTrackerAccessRole'):
            iam.Role(self, 'DeadlineResourceTrackerRole',
                assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
                managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name(
                    'AWSThinkboxDeadlineResourceTrackerAccessPolicy')],
                role_name='DeadlineResourceTrackerAccessRole'
            )
        
        
        # for az in vpc.availability_zones:
        #     subnet_list.append(
        #         ec2.PrivateSubnet(self, 'deadline-render-worker-subnet',
        #             availability_zone=az,
        #             cidr_block=20,
        #             vpc_id=vpc.vpc_id,
        #         )
        #     )

        render_worker_sg = ec2.SecurityGroup(self, 'Deadline-Render-Worker-SG',
            vpc=vpc, security_group_name='Deadline-Render-Worker-SG')
        # render_worker_sg.connections.allow_from(
        #     ec2.Connections(
        #         security_groups=[deadline.RenderQueueSecurityGroups.backend]
        #     ),
        #     ec2.Port.tcp(4433),
        # )



        ##
        # Export Stack Outputs for Cross-Stack References
        ##
        cdk.CfnOutput(self, 'rfdk-vpc-id',
            value=vpc.vpc_id,
            export_name='rfdk-vpc-id'
        )

        cdk.CfnOutput(self, 'rfdk-render-queue',
            value=render_queue.to_string(),
            export_name='rfdk-render-queue'
        )


        ##
        # Database connection
        ##
        # dbc = deadline.DatabaseConnection()

        # dbc.for_doc_db()