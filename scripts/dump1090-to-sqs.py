#!/usr/bin/env python3
from socket import socket
from sys import exit
from json import dumps as json_encode
from boto3 import resource
from botocore.exceptions import EndpointConnectionError
from os import environ, system, name
from uuid import uuid4
from time import strftime, sleep

# Settings of dump1090
TCP_IP = 'localhost'
TCP_PORT = 30003
BUFFER_SIZE = 65536
RECIEVE_INTERVAL = 1.00 # seconds

# Settings of SQS
QUEUE_URL = environ['QUEUE_URL']
BATCH_SIZE = 10

# Text settings
CHARACTER_ENCODING = 'utf-8'
LINE_DELIMETER = '\r\n'
COLUMN_DELIMETER = ','
SPACE_CHARACTER = ' '
EMPTY_STRING = ''

# Settings of ADS-B messages
MESSAGE_STRUCTURE = {
    'IcaoAddress': 4,
    'Date': 8,
    'Time': 9,
    'FlightLevel': 11,
    'Heading': 13,
    'Latitude': 14,
    'Longitude': 15,
}


# Transform an comma-delimted ADS-B message to a JSON object
def convert_to_json(line):
    columns = line.split(COLUMN_DELIMETER)

    return {
        key: columns[index].strip(SPACE_CHARACTER)
        for key, index in MESSAGE_STRUCTURE.items()
        if index < len(columns) and columns[index] != EMPTY_STRING
    }


# Determine if required attributes are present and at least one optional attribute
def is_valid(record):
    return 'IcaoAddress' in record and \
        'Date' in record and \
        'Time' in record and \
        len(record.keys()) > 3


# Prepares the message to be send to SQS
def convert_to_sqs_entry(record):
     return {
        'Id': str(uuid4()),
        'MessageBody': json_encode(record),
     }


# Writes to the screen
def log(message, override=True):
    # After each message return to the start of the line again, so the log won't build up over time
    # The longest message is 34 character, so pad all other messages
    print(' [{}] - {:34}'.format(strftime('%Y-%m-%d %H:%M:%S'), message), end='\r' if override else '\n')


# Receive messages from dump1090 socket
def receive_messages(dump1090):
    # Wait for new messags to become available on the socket
    sleep(RECIEVE_INTERVAL)

    # Receive raw bytes
    buffer = dump1090.recv(BUFFER_SIZE)

    # Convert, strip and split the buffer
    lines = buffer.decode(CHARACTER_ENCODING).strip(LINE_DELIMETER).split(LINE_DELIMETER)

    # Transform comma seperated lines into list of JSON objects
    return [
        convert_to_json(line)
        for line in lines
    ]


# Process and send messages to SQS
def send_messages(queue, messages):
    # Filter out message without any additional information (other than ICAO address)
    entries = [
        convert_to_sqs_entry(message)
        for message in messages
        if is_valid(message)
    ]

    # Create batches of 10 messages
    batches = [
        entries[i:i + BATCH_SIZE]
        for i in range(0, len(entries), BATCH_SIZE)
    ]

    # Send to SQS
    try:
        for batch in batches:
            queue.send_messages(
                Entries=batch,
            )
        log('Sent {} messages'.format(len(entries)))

    except EndpointConnectionError:
        log('No internet connection')


# Only run when the script is invoked directly
if __name__ == '__main__':
    # Connection to the socket
    dump1090 = socket()
    try:
        dump1090.connect((TCP_IP, TCP_PORT))
        log('Successfully connected to dump1090')
    except:
        log('Failed to connect to dump1090', override=False)
        exit()

    # SQS client
    queue = resource('sqs').Queue(QUEUE_URL)

    # Continous loop
    try:
        while True:
            messages = receive_messages(dump1090)
            send_messages(queue, messages)

    # Graceful exit
    except KeyboardInterrupt:
        log('Shutting down', override=False)
        exit()
