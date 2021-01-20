#!/usr/bin/env python3
from boto3 import resource
from boto3.dynamodb.conditions import Attr
from os import environ
from datetime import datetime, timedelta
from json import dumps as json_dump

# Time format used in ADS-B
TIME_FORMAT = '%Y/%m/%d %H:%M:%S'

if 'TABLE_NAME' in environ:
    dynamodb = resource('dynamodb')
    table = dynamodb.Table(environ['TABLE_NAME'])
else:
    exit('Environment variable "TABLE_NAME" not set')


def handler(event, context):
    time_threshold = datetime.now() - timedelta(minutes=5)

    response = table.scan(
        ProjectionExpression='FlightCode, FlightLevel, AirSpeed, Heading, Latitude, Longitude, Squawk',
        FilterExpression=Attr('LastUpdated').gte(time_threshold.strftime(TIME_FORMAT)) &
            Attr('Latitude').exists() & Attr('Longitude').exists()
    )

    items = response['Items'] if 'Items' in response else []

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': 'http://[::1]',
        },
        'body': json_dump(items, default=str)
    }
