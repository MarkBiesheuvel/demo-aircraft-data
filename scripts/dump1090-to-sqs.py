#!/usr/bin/env python3
from socket import socket
from sys import exit
from json import dumps as json_encode
from boto3 import resource
from os import environ

# Settings of dump1090
TCP_IP = 'localhost'
TCP_PORT = 30003
BUFFER_SIZE = 102400

# Settings of SQS
QUEUE_URL = environ['QUEUE_URL']

# Text settings
CHARACTER_ENCODING = 'utf-8'
LINE_DELIMETER = '\r\n'
COLUMN_DELIMETER = ','
SPACE_CHARACTER = ' '
EMPTY_STRING = ''

# Settings of ADS-B messages
MESSAGE_STRUCTURE = {
    'IcaoAddress': 4,
    'FlightCode': 10,
    'FlightLevel': 11,
    'AirSpeed': 12,
    'Heading': 13,
    'Latitude': 14,
    'Longitude': 15,
    'Squawk': 16,
}


# Transform an comma-delimted ADS-B message to a JSON object
def transform(line):
    columns = line.split(COLUMN_DELIMETER)

    return {
        key: columns[index].strip(SPACE_CHARACTER)
        for key, index in MESSAGE_STRUCTURE.items()
        if index < len(columns) and columns[index] != EMPTY_STRING
    }


# Connection to the socket
dump1090 = socket()
try:
    dump1090.connect((TCP_IP, TCP_PORT))
    print('Successfully connected to dump1090')
except:
    print('Failed to connect to dump1090')
    exit()

# SQS client
queue = resource('sqs').Queue(QUEUE_URL)

# Continous loop
while True:
    # Receive raw bytes
    buffer = dump1090.recv(BUFFER_SIZE)

    # Convert, strip and split the buffer
    lines = buffer.decode(CHARACTER_ENCODING).strip(LINE_DELIMETER).split(LINE_DELIMETER)

    # Transform comma seperated lines into list of JSON objects
    records = [
        transform(line)
        for line in lines
    ]

    # Filter out message without any additional information (other than ICAO address)
    records = [
        record
        for record in records
        if len(record.keys()) > 1
    ]

    # TODO: switch to batch sending
    for record in records:
        queue.send_message(
            MessageBody=json_encode(record)
        )
