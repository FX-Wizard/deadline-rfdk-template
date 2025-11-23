import aws_cdk as cdk
import random
from dataclasses import dataclass
from typing import Mapping, Optional
from aws_cdk import (
    Stack,
    CfnOutput,
    aws_efs as efs,
    aws_fsx as fsx,
    aws_ec2 as ec2,
)
from constructs import Construct


@dataclass 
class StorageStackProps(cdk.StackProps):
    vpc: Optional[ec2.IVpc] = None
    vpc_id: Optional[str] = None
    enable_fsx_zfs: bool = True
    enable_efs: bool = False


class StorageStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, props: StorageStackProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = props.vpc

        # Create storage security group
        self.nfs_sg = ec2.SecurityGroup(
            self,
            "RenderFarmStorageSG",
            vpc=self.vpc,
            description="Allow access to EFS and FSx for render farm",
            allow_all_outbound=False
        )

        # Allow NFS inbound from VPC
        self.nfs_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(2049),
            description="Allow NFS TCP access inbound from VPC"
        )
        self.nfs_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.udp(2049),
            description="Allow NFS UDP access inbound from VPC"
        )

        # Allow FSx ZFS additional ports
        self.nfs_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp_range(111, 111),
            description="RPC portmapper"
        )
        self.nfs_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.udp(111),
            description="RPC portmapper UDP"
        )

        self.nfs_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp_range(20001, 20003),
            description="FSx ZFS NFS auxiliary ports"
        )
        self.nfs_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.udp_range(20001, 20003),
            description="FSx ZFS NFS auxiliary UDP ports"
        )

        if props.enable_fsx_zfs:
            self.deploy_zfs()

        if props.enable_efs:
            self.deploy_efs()

    def deploy_zfs(self):
        # FSx ZFS File System
        self.fsx_zfs = fsx.CfnFileSystem(
            self,
            "ZfsFileSystem",
            file_system_type="OPENZFS",
            subnet_ids=get_random_subnet_ids(self.vpc, 2),
            storage_capacity=128,
            open_zfs_configuration=fsx.CfnFileSystem.OpenZFSConfigurationProperty(
                deployment_type="MULTI_AZ_1",
                throughput_capacity=160,  # MB/s
                preferred_subnet_id=self.vpc.private_subnets[0].subnet_id,
                root_volume_configuration=fsx.CfnFileSystem.RootVolumeConfigurationProperty(
                    nfs_exports=[
                        fsx.CfnFileSystem.NfsExportsProperty(
                            client_configurations=[
                                fsx.CfnFileSystem.ClientConfigurationsProperty(
                                    clients=self.vpc.vpc_cidr_block,
                                    options=["rw", "no_root_squash"]
                                )
                            ]
                        )
                    ]
                )
            ),
            security_group_ids=[self.nfs_sg.security_group_id]
        )

        # Public properties for cross-stack reference
        self.fsx_file_system_id = self.fsx_zfs.ref
        self.fsx_dns_name = self.fsx_zfs.attr_dns_name
        
        # Output FSx connection details
        CfnOutput(
            self,
            "FsxFileSystemId",
            value=self.fsx_file_system_id,
            description="FSx ZFS File System ID"
        )
        
        CfnOutput(
            self,
            "FsxDnsName",
            value=self.fsx_dns_name,
            description="FSx ZFS DNS Name for mounting"
        )

    def deploy_efs(self):
        # EFS File System
        self.efs_filesystem = efs.FileSystem(
            self,
            "EfsFileSystem",
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_group=self.nfs_sg,
            enable_automatic_backups=False
        )

        # Public properties for cross-stack reference
        self.efs_file_system_id = self.efs_filesystem.file_system_id

        # Output EFS connection details
        CfnOutput(
            self,
            "EfsFileSystemId",
            value=self.efs_file_system_id,
            description="EFS File System ID"
        )


def get_random_subnet_ids(vpc: ec2.IVpc, count: int = 2) -> list[str]:
    return [subnet.subnet_id for subnet in random.sample(vpc.private_subnets, min(count, len(vpc.private_subnets)))]
