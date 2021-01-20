#!/usr/bin/env python3
from aws_cdk import (
    core,
    aws_apigateway as apigateway,
    aws_cloudfront as cloudfront,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_sqs as sqs,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
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
        table.grant_read_write_data(lambda_role)

        # Integration between SQS and Lambda
        event = lambda_event_sources.SqsEventSource(
            queue=queue,
            batch_size=10,
        )

        # Lambda function that processes messages from SQS queue and updates DynamoDB table
        import_function = lambda_.Function(
            self, 'ImportFunction',
            description='Reads SQS messages and writes to DynamoDB',
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_asset('lambda_import/'),
            timeout=message_timeout,
            handler='index.handler',
            role=lambda_role,
            events=[event],
            environment={
                'TABLE_NAME': table.table_name,
            },
        )

        # TODO: add custom log group
        # TODO: add metric filters for number of succesfull updates and failed updates

        # Lambda function that reads from DynamoDB and returns data to API Gateway
        api_function = lambda_.Function(
            self, 'ApiFunction',
            description='Reads from DynamoDB and returns to API GW',
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_asset('lambda_api/'),
            timeout=message_timeout,
            handler='index.handler',
            role=lambda_role,
            environment={
                'TABLE_NAME': table.table_name,
            },
        )

        # API Gateway for requesting aircraft data
        api = apigateway.RestApi(
            self, 'Api',
            endpoint_types=[
                apigateway.EndpointType.REGIONAL
            ],
            cloud_watch_role=False,
        )

        aircraft_resource = api.root.add_resource('aircraft')

        aircraft_resource.add_method(
            http_method='GET',
            integration=apigateway.LambdaIntegration(
                api_function,
                proxy=True,
            ),
        )

        # Static website
        bucket = s3.Bucket(self, 'StaticWebsite')

        s3_deployment.BucketDeployment(
            self, 'Deployment',
            sources=[
                s3_deployment.Source.asset('html/'),
            ],
            destination_bucket=bucket,
        )

        # Permissions between CloudFront and S3
        origin_identity = cloudfront.OriginAccessIdentity(self, 'Identity')
        bucket.grant_read(origin_identity.grant_principal)


        # CloudFront distribution pointing to both S3 and API Gateway
        s3_origin = cloudfront.SourceConfiguration(
            s3_origin_source=cloudfront.S3OriginConfig(
                s3_bucket_source=bucket,
                origin_access_identity=origin_identity,
            ),
            behaviors=[
                cloudfront.Behavior(
                    default_ttl=core.Duration.days(0),
                    min_ttl=core.Duration.days(0),
                    max_ttl=core.Duration.days(31),
                    is_default_behavior=True,
                )
            ]
        )

        api_origin = cloudfront.SourceConfiguration(
            origin_path='/{}'.format(api.deployment_stage.stage_name),
            custom_origin_source=cloudfront.CustomOriginConfig(
                domain_name='{}.execute-api.{}.{}'.format(
                    api.rest_api_id,
                    self.region,
                    self.url_suffix
                ),
            ),
            behaviors=[
                cloudfront.Behavior(
                    default_ttl=core.Duration.seconds(0),
                    min_ttl=core.Duration.seconds(0),
                    max_ttl=core.Duration.seconds(0),
                    path_pattern='/aircraft/*',
                )
            ]
        )

        cloudfront.CloudFrontWebDistribution(
            self, 'CDN',
            price_class=cloudfront.PriceClass.PRICE_CLASS_ALL,
            origin_configs=[
                s3_origin,
                api_origin,
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
