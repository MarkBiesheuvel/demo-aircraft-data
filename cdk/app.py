#!/usr/bin/env python3
from aws_cdk import (
    core,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_sqs as sqs,
)


class DemoStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Message timeout; used by SQS and Lambda
        message_timeout = core.Duration.seconds(15)

        # SQS queue that the Raspberry Pi will write to
        queue = sqs.Queue(
            self, 'Queue',
            visibility_timeout=message_timeout,
            receive_message_wait_time=core.Duration.seconds(20),
            retention_period=core.Duration.days(14), # TODO: decrease retention after done development
        )

        # DynamoDB table that the web app will read from
        icao_address = dynamodb.Attribute(
            name='IcaoAddress',
            type=dynamodb.AttributeType.STRING,
        )
        table = dynamodb.Table(
            self, 'Table',
            partition_key=icao_address,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=core.RemovalPolicy.DESTROY,
        )

        # IAM user for the Raspberry Pi
        user = iam.User(self, 'RaspberryPi')
        queue.grant_send_messages(user)
        access_key = iam.CfnAccessKey(
            self, 'AccessKey',
            user_name=user.user_name,
        )

        # IAM role for Lambda function, so it can write to DynamoDB
        lambda_role = iam.Role(
            self, 'LambdaRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'),
            ],
        )
        table.grant_write_data(lambda_role)

        # Integration between SQS and Lambda
        event = lambda_event_sources.SqsEventSource(
            queue=queue,
            batch_size=10,
        )

        # Lambda function that processes messages from SQS queue and updates DynamoDB table
        function = lambda_.Function(
            self, 'Function',
            description='Reads SQS messages and writes to DynamoDB',
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_asset('lambda/'),
            timeout=message_timeout,
            handler='index.handler',
            role=lambda_role,
            environment={
                'TABLE_NAME': table.table_name,
            },
            events=[
                event,
            ],
        )

        # Outputs that are needed on the Raspberry Pi
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
