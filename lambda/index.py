#!/usr/bin/env python3
from boto3 import resource
from os import environ
from json import loads as json_decode, dumps as json_encode

RESERVED_MESSAGE_ATTRIBUTES = ['IcaoAddress', 'Date', 'Time']

if 'TABLE_NAME' in environ:
    dynamodb = resource('dynamodb')
    table = dynamodb.Table(environ['TABLE_NAME'])
else:
    exit('Environment variable "TABLE_NAME" not set')


def process_record(record):
    message = json_decode(record['body'])

    # Skip messages that miss the required attributes
    for attribute in RESERVED_MESSAGE_ATTRIBUTES:
        if attribute not in message:
            return

    # Get the Partition Key
    key = {
        'IcaoAddress': message['IcaoAddress']
    }

    # Generate update expression and attributes values from the message
    update_expression = 'SET ' + ', '.join([
        '{0} = :{1}, {0}LastUpdated = :datetime'.format(key, key.lower())
        for key in message.keys()
        if key not in RESERVED_MESSAGE_ATTRIBUTES
    ])
    attribute_values = {
        ':{0}'.format(key.lower()): value
        for key, value in message.items()
        if key not in RESERVED_MESSAGE_ATTRIBUTES
    }
    attribute_values[':datetime'] = '{0} {1}'.format(message['Date'], message['Time'])

    table.update_item(
        Key=key,
        UpdateExpression=update_expression,
        ExpressionAttributeValues=attribute_values,
    )


def handler(event, context):
    # Exit if this is a non SQS invocation
    if 'Records' not in event:
        return

    for record in event['Records']:
        process_record(record)
