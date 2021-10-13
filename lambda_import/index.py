#!/usr/bin/env python3
from boto3 import client
from os import environ
from datetime import datetime
from json import loads as json_decode, dumps as json_encode

# Time format used in ADS-B
TIME_FORMAT = '%Y/%m/%d %H:%M:%S.%f %z'
CURRENT_UTC_OFFSET = '+0200'

# Attributes that stay constant
DIMENSION_ATTRIBUTES = [
    {
        'Name': 'IcaoAddress',
        'Type': 'VARCHAR'
    }
]

# Attributes that differ over time
MEASURE_ATTRIBUTES = [
    {
        'Name': 'FlightLevel',
        'Type': 'BIGINT'
    },
    {
        'Name': 'Heading',
        'Type': 'BIGINT'
    },
    {
        'Name': 'Latitude',
        'Type': 'DOUBLE'
    },
    {
        'Name': 'Longitude',
        'Type': 'DOUBLE'
    }
]

if 'TABLE_NAME' in environ:
    database_name, table_name = environ['TABLE_NAME'].split('|')
    timestream = client('timestream-write')
else:
    exit('Environment variable "TABLE_NAME" not set')


def process_message(record):
    message = json_decode(record['body'])

    # Skip messages that miss the required attributes
    if 'Date' not in message or 'Time' not in message:
        return []

    time = datetime.strptime('{} {} {}'.format(message['Date'], message['Time'], CURRENT_UTC_OFFSET), TIME_FORMAT)
    milliseconds = int(time.timestamp() * 1000)

    return [
        {
            'Dimensions': [
                {
                    'Name': dimension['Name'],
                    'Value': message[dimension['Name']],
                    'DimensionValueType': dimension['Type']
                }
                for dimension in DIMENSION_ATTRIBUTES
                if dimension['Name'] in message
            ],
            'MeasureName': measure['Name'],
            'MeasureValue': message[measure['Name']],
            'MeasureValueType': measure['Type'],
            'Time': str(milliseconds),
            'TimeUnit': 'MILLISECONDS'
        }
        for measure in MEASURE_ATTRIBUTES
        if measure['Name'] in message
    ]


def handler(event, context):
    # Exit if this is a non SQS invocation
    if 'Records' not in event:
        return

    # Each message from SQS can generate multiple records in Timestream, so let's rename the variable
    messages = event['Records']

    records = [
        record
        for message in messages
        for record in process_message(message)
    ]

    if len(records) > 0:
        try:
            timestream.write_records(
                DatabaseName=database_name,
                TableName=table_name,
                CommonAttributes={},
                Records=records,
            )
        except timestream.exceptions.RejectedRecordsException as exception:
            for record in exception.response['RejectedRecords']:
                print(record['Reason'])
