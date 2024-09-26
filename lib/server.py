from .platform import DiscocraftainerPlatform
from constructs import Construct
from aws_cdk import (
    aws_ecs as ecs,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_ecs_patterns as ecs_patterns,
    aws_route53 as route53,
    Stack,
    Environment,
    Duration,
    aws_elasticloadbalancingv2 as elbv2
)
import os
import dotenv

dotenv.load_dotenv()

server_port = int(os.environ['SERVER_PORT'])

class Discocraftainer(Stack):
    def __init__(self, scope: Construct, id: str, env: Environment, **kwargs) -> None:
        super().__init__(scope, id, env=env, **kwargs)
        
        self.platform = DiscocraftainerPlatform(self, "DiscocraftainerPlatform", env=env)
        
        # create a role for the task to use for logging
        self.task_role = iam.Role(
            self, "MinecraftContainerRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com")
        )
        
        # create a policy to allow the task to log to cloudwatch
        self.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                resources=["*"]
            ),
        )
        
        # now we will define the ECS fargate service which will run both our
        # minecraft server and the watchdog container
        self.task_definition = ecs.FargateTaskDefinition(
            self, "DiscocraftainerTaskDef",
            cpu=1024,
            memory_limit_mib=2048,
            task_role=self.task_role,
            execution_role=self.task_role,
        )
         
        
        # add the minecraft container to the task definition
        self.minecraft_container = self.task_definition.add_container(
            "MinecraftContainer",
            image=ecs.ContainerImage.from_registry("itzg/minecraft-server"),
            environment={
                "EULA": "TRUE",
            },
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="Minecraft"
            )
        )
        
        self.minecraft_container.add_port_mappings(
            ecs.PortMapping(container_port=server_port, protocol=ecs.Protocol.TCP)
        )
        
        # configure the subdomain
        self.hosted_zone = route53.HostedZone.from_lookup(
            self, "OuradioHostedZone",
            domain_name="ouradio.net"
        )
        
        # create the service security group
        self.service_sg = ec2.SecurityGroup(
            self, "DiscocraftainerServiceSecurityGroup",
            vpc=self.platform.vpc,
            allow_all_outbound=True
        )
        
        self.service_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(server_port),
            "Allow TCP on port " + str(server_port)
        )
        
        # now lets define the fargate service which will run our task definition
        self.service = ecs_patterns.NetworkLoadBalancedFargateService(
            self, "DiscocraftainerService",
            cluster=self.platform.cluster,
            task_definition=self.task_definition,
            desired_count=1,
            domain_name="minecraft.ouradio.net",
            domain_zone=self.hosted_zone,
            listener_port=int(server_port),
            public_load_balancer=True,
            assign_public_ip=True,
            security_groups=[self.service_sg],
            )
        
        # configure the health check for the target group
        self.service.target_group.configure_health_check(
            port=str(server_port),
            protocol=elbv2.Protocol.TCP,
            healthy_threshold_count=2,
            unhealthy_threshold_count=2,
            timeout=Duration.seconds(10)
        )