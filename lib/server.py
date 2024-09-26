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
    aws_elasticloadbalancingv2 as elbv2,
    aws_efs as efs,
    RemovalPolicy
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
        
        # create a file system for the minecraft server
        self.file_system = efs.FileSystem(
            self, "DiscocraftainerFileSystem",
            vpc=self.platform.vpc,
            removal_policy=RemovalPolicy.SNAPSHOT,
            )
        
        # create an access point for the file system
        self.access_point = self.file_system.add_access_point(
            "DiscocraftainerAccessPoint",
            path="/minecraft",
            posix_user={
                "uid": "1000",
                "gid": "1000"
            },
            create_acl={
                "owner_gid": "1000",
                "owner_uid": "1000",
                "permissions": "0755"
            }
        )
        
        # attach the efs read/write to the task role
        self.task_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowReadWriteOnEFS",
                actions=[
                    "elasticfilesystem:ClientMount",
                    "elasticfilesystem:ClientWrite",
                    "elasticfilesystem:DescribeFileSystems",
                ],
                resources=[self.file_system.file_system_arn],
                conditions={
                    "StringEquals": {
                        "elasticfilesystem:AccessPointArn": self.access_point.access_point_arn
                    }
                }
            )
        )
        
        # now we will define the ECS fargate task which will run both our
        # minecraft server and the watchdog container using the task role
        self.task_definition = ecs.FargateTaskDefinition(
            self, "DiscocraftainerTaskDef",
            cpu=1024,
            memory_limit_mib=2048,
            task_role=self.task_role,
            execution_role=self.task_role,
            # add the efs volume to the task definition
            volumes=[
                ecs.Volume(
                    name="data",
                    efs_volume_configuration=ecs.EfsVolumeConfiguration(
                        file_system_id=self.file_system.file_system_id,
                        transit_encryption='ENABLED',
                        authorization_config=ecs.AuthorizationConfig(
                            access_point_id=self.access_point.access_point_id,
                            iam='ENABLED'
                        )
                    )
                )
            ]
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
        
        # add efs mount points to the minecraft container
        self.minecraft_container.add_mount_points(
            ecs.MountPoint(
                container_path="/data",
                source_volume="data",
                read_only=False
            )
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
        
        # allow the service receive traffic on the server port
        self.service_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(server_port),
            "Allow TCP on port " + str(server_port)
        )
        
        # add ingress rule for efs to task communication
        self.file_system.connections.allow_from(
            self.service_sg,
            ec2.Port.tcp(2049),
            "Allow EFS communication"
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