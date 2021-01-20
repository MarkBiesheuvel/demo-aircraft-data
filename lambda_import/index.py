#!/usr/bin/env python3
from boto3 import resource
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from os import environ
from functools import reduce
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
    icao_address = message['IcaoAddress']
    key = {
        'IcaoAddress': icao_address
    }

    # Generate update expression to set both the ${Attribute} as well as ${Attribute}LastUpdated
    update_expression = 'SET LastUpdated = :datetime, ' + \
        ', '.join([
            '{0} = :{1}, {0}LastUpdated = :datetime'.format(attribute, attribute.lower())
            for attribute in message.keys()
            if attribute not in RESERVED_MESSAGE_ATTRIBUTES
        ])

    # Only update this item if the date time in the record is after the ${Attribute}LastUpdated value
    condition_expression = reduce(
        lambda a, b: a & b, (
            Attr(attribute).not_exists() | Attr(attribute).lte(':datetime')
            for attribute in message.keys()
            if attribute not in RESERVED_MESSAGE_ATTRIBUTES
        )
    )

    # Specify the values of the Attributes
    attribute_values = {
        ':{0}'.format(attribute.lower()): value
        for attribute, value in message.items()
        if attribute not in RESERVED_MESSAGE_ATTRIBUTES
    }

    # Lastly, also add the date and time of the record, used in both UpdateExpression and ConditionExpression
    attribute_values[':datetime'] = '{0} {1}'.format(message['Date'], message['Time'])

    try:
        table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ConditionExpression=condition_expression,
            ExpressionAttributeValues=attribute_values,
        )

        # Success
        print('Succesfully updated {0}'.format(icao_address))

    except ClientError as e:
        # Catch any condition failures; this means the record was out of date
        if e.response['Error']['Code']=='ConditionalCheckFailedException':
            print('Failed to update {0}, as the message is out-dated'.format(icao_address))

        # Reraise any other ClientError so it will show up in monitoring and logging
        else:
            raise e


def handler(event, context):
    # Exit if this is a non SQS invocation
    if 'Records' not in event:
        return

    for record in event['Records']:
        process_record(record)
