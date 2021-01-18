#!/usr/bin/env python3
from boto3 import resource
from os import environ
from json import loads as json_decode, dumps as json_encode

if 'TABLE_NAME' in environ:
    dynamodb = resource('dynamodb')
    table = dynamodb.Table(environ['TABLE_NAME'])
else:
    exit('Environment variable "TABLE_NAME" not set')


def handler(event, context):
    # print(json_encode(event))

    # Exit if this is a non SQS invocation
    if 'Records' not in event:
        return

    records = event['Records']

    for record in records:
        message = json_decode(record['body'])

        # Skip invalid messages
        if 'IcaoAddress' not in message:
            continue

        # Get the Partition Key
        key = {
            'IcaoAddress': message['IcaoAddress']
        }

        # Generate update expression and attributes values from the message
        update_expression = 'SET ' + ', '.join([
            '{} = :{}'.format(key, key.lower())
            for key in message.keys()
            if key != 'IcaoAddress'
        ])
        attribute_values = {
            ':{}'.format(key.lower()): value
            for key, value in message.items()
            if key != 'IcaoAddress'
        }

        table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=attribute_values,
        )
