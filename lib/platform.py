from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
    Stack,  
)
from constructs import Construct

class DiscoCraftainerPlatform(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        # Define your VPC
        self.vpc = ec2.Vpc(self, "DiscoCraftainerVPC",
                      vpc_name="DiscoCraftainerVPC",
                      max_azs=3, # Default is all AZs in the region
                      nat_gateways=0,
                      )
        # Define your ECS Cluster
        self.cluster = ecs.Cluster(self, "DiscoCraftainerCluster",
                            cluster_name="DiscoCraftainerCluster",
                            vpc=self.vpc,
                            # container_insights=True
                            )
        # Add other resources and configurations here