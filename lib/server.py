from .platform import DiscoCraftainerPlatform
from constructs import Construct
from aws_cdk import (
    aws_ecs as ecs,
    aws_iam as iam,
    Stack,
    aws_ec2 as ec2,
)

class DiscoCraftainer(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        self.platform = DiscoCraftainerPlatform(self, "DiscoCraftainerPlatform")
        
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
            self, "DiscoCraftainerTaskDef",
            cpu=1024,
            memory_limit_mib=2048,
            task_role=self.task_role,
            execution_role=self.task_role
        )       
         
        
        # add the minecraft container to the task definition
        self.minecraft_container = self.task_definition.add_container(
            "MinecraftContainer",
            image=ecs.ContainerImage.from_registry("itzg/minecraft-server"),
            environment={
                "EULA": "TRUE"
            },
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="Minecraft"
            )
        )
        
        self.minecraft_container.add_port_mappings(
            ecs.PortMapping(container_port=25565, host_port=25565, protocol=ecs.Protocol.TCP)
        )
        
        # # now we will add a watchdog container to the task defintion
        # # this container is responsible for monitoring the minecraft server
        # # and when it has been idle for config.MINECRAFT_IDLE_TIMEOUT seconds
        # # it will stop the server (set the desired task count to 0)
        # self.watchdog_container = self.task_definition.add_container(
        #     "WatchdogContainer",
        #     image=ecs.ContainerImage.from_asset("watchdog"),
        #     environment={
        #         "MINECRAFT_IDLE_TIMEOUT": str(config.MINECRAFT_IDLE_TIMEOUT),
        #         "CLUSTER": self.platform.cluster.cluster_name,
        #         "SERVICE": self.service.service_name
        #     },
        #     logging=ecs.LogDrivers.aws_logs(
        #         stream_prefix="Watchdog"
        #     )
        # )
        
        # now lets define the fargate service which will run our task definition
        self.service = ecs.FargateService(
            self, "DiscoCraftainerService",
            cluster=self.platform.cluster,
            task_definition=self.task_definition,
            desired_count=1,
            assign_public_ip=True
        )
        
        self.service.connections.allow_from_any_ipv4(
            ec2.Port.tcp(25565)
        )