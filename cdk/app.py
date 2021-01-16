#!/user/bin/env python3
from aws_cdk import (
    core,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_sqs as sqs,
)


class DemoStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        user = iam.User(self, 'RaspberryPi')

        access_key = iam.CfnAccessKey(
            self, 'AccessKey',
            user_name=user.user_name,
        )

        icao_address = dynamodb.Attribute(
            name='IcaoAddress',
            type=dynamodb.AttributeType.STRING,
        )

        queue = sqs.Queue(
            self, 'Queue',
            visibility_timeout=core.Duration.seconds(10),
            receive_message_wait_time=core.Duration.seconds(20),
            retention_period=core.Duration.minutes(4),
        )

        queue.grant_send_messages(user)

        table = dynamodb.Table(
            self, 'Table',
            partition_key=icao_address,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=core.RemovalPolicy.DESTROY,
        )

        core.CfnOutput(
            self, 'QueueUrl',
            value=queue.queue_url,
        )

        core.CfnOutput(
            self, 'AccessKeyId',
            value=access_key.ref,
        )

        core.CfnOutput(
            self, 'SecretAccessKey',
            value=access_key.attr_secret_access_key,
        )

        core.CfnOutput(
            self, 'Region',
            value=self.region,
        )


app = core.App()
stack = DemoStack(app, 'AircraftData')
app.synth()
