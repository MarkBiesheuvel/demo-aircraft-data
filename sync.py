#!/usr/bin/env python3
from socket import socket
from sys import exit
from json import dumps as json_encode

# Settings of dump1090
TCP_IP = 'localhost'
TCP_PORT = 30003
BUFFER_SIZE = 102400
CHARACTER_ENCODING = 'utf-8'
LINE_DELIMETER = '\r\n'
COLUMN_DELIMETER = ','


# Transform an comma-delimted ADS-B message to a JSON object
def transform(line):
    columns = line.split(COLUMN_DELIMETER)

    record = {
        'IcaoAddress': columns[4]
    }

    if columns[10] != '':
        record['FlightCode'] = columns[10].strip()

    if columns[11] != '':
        record['FlightLevel'] = columns[11].strip()

    if columns[12] != '':
        record['AirSpeed'] = columns[12]

    if columns[13] != '':
        record['Heading'] = columns[13]

    if columns[14] != '':
        record['Latitude'] = columns[14]

    if columns[15] != '':
        record['Longitude'] = columns[15]

    if columns[16] != '':
        record['Squawk'] = columns[16]

    return record


# Connection to the socket
dump1090 = socket()
try:
    dump1090.connect((TCP_IP, TCP_PORT))
    print('Successfully connected to dump1090')
except:
    print('Failed to connect to dump1090')
    exit()

# Continous loop
while True:
    # Receive raw bytes
    buffer = dump1090.recv(BUFFER_SIZE)

    # Convert, strip and split the buffer
    lines = buffer.decode(CHARACTER_ENCODING).strip(LINE_DELIMETER).split(LINE_DELIMETER)

    records = [
        transform(line)
        for line in lines
    ]

    for record in records:
        if len(record.keys()) > 1:
            print(record)
