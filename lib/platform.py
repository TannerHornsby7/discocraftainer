from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
    Stack,
    Environment
)
from constructs import Construct

class DiscocraftainerPlatform(Stack):
    def __init__(self, scope: Construct, id: str, env: Environment, **kwargs) -> None:
        super().__init__(scope, id, env=env, **kwargs)

        # Create a VPC for the service
        self.vpc = ec2.Vpc(
            self, "DiscocraftainerVPC",
            vpc_name="DiscocraftainerVPC",
            max_azs=3,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                )
            ],
            enable_dns_hostnames=True,
            enable_dns_support=True
        )
        
        # create a cluster for the service
        self.cluster = ecs.Cluster(self, "DiscocraftainerCluster",
            vpc = self.vpc,
            cluster_name="DiscocraftainerCluster",
            container_insights=True
        )
        