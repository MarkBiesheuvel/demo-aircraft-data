# Demo: Real-time aircraft data ingestion to AWS

This demo uses a [Raspberry Pi](https://www.raspberrypi.org/) and [RTL-SDR](https://www.rtl-sdr.com/) dongle to receive ADS-B messages. These messages are broadcast by aircrafts on 1090 MHz. To decode the signal the Raspberry Pi runs a program called [dump1090](https://www.satsignal.eu/raspberry-pi/dump1090.html). This program makes the message available on port 30003 by default. Therefore, we run a Python script that listens on that port, transforms the message to JSON and forwards this to [AWS SQS](https://aws.amazon.com/sqs/).

This demo was base on the [Kinesis demo of Wouter Liefting](http://www.demo.wlid.nl.s3-website.eu-central-1.amazonaws.com/kinesis-explanation.html).

## 1. Raspberry Pi

For this demo we will need to download and build both `rtl-sdr` and `dump1090`.

### 1.1 Installing build tools

Start with updating our system and installing the build tools.

```sh
sudo apt update
sudo apt upgrade
sudo apt install git cmake libusb-1.0-0-dev build-essential
```

### 1.2 Building rtl-sdr

Next, download the source code for rtl-sdr and build it.

```sh
cd ~
git clone git://git.osmocom.org/rtl-sdr.git
cd rtl-sdr
mkdir build
cd build
cmake ../ -DINSTALL_UDEV_RULES=ON
make
sudo make install
sudo ldconfig
```

Now that we have a working build, we need to grant our user access to the device.
```sh
sudo cp ~/rtl-sdr/rtl-sdr.rules /etc/udev/rules.d/
sudo usermod -a -G plugdev $(whoami)
sudo reboot
```

### 1.3 Building dump1090

Next, download the source code for dump1090 and build it.

```sh
cd ~
git clone git://github.com/MalcolmRobb/dump1090.git
cd dump1090
make
```

### 1.4 Downloading Python script

Download the sync python script.

```sh
wget -q -O ~/dump1090-to-sqs.py https://raw.githubusercontent.com/MarkBiesheuvel/demo-aircraft-data/master/scripts/dump1090-to-sqs.py
python3 -m pip install boto3
```

## 2 AWS infrastructure

To deploy the AWS infrastructure we will use the AWS Cloud Development Kit (CDK).

### 2.1 Deploying resources

In order to run this command, our computer should be configured with an IAM user with AdministratorAccess.

Note replace with your own account id.

```sh
sudo npm install -g aws-cdk --update
python3 -m pip install -r cdk/requirements.txt
cdk bootstrap aws://418155680583/eu-west-1
cdk deploy
```

### 2.2 Configuring Raspberry Pi

Next, configure the queue url, region, and access key and secret in on the Raspberry Pi.
To do this we run a script on our computer which generates a set of command that we need to run on the Raspberry Pi.

```sh
sh scripts/configure.sh
```

The output of this command needs to be copied, pasted and ran on the Raspberry Pi. The output should look something like this:

```sh
export QUEUE_URL='https://sqs.eu-west-1.amazonaws.com/.../...'
aws configure set aws_access_key_id 'AKIA...'
aws configure set aws_secret_access_key '...'
aws configure set region 'eu-west-1'
```

### 2.3 Manual resources

Currently (January 2021) the demo relies on two manually created resources. Since Amazon Location Service is in Preview and does not have CloudFormation support yet, I (Mark Biesheuvel) have created a Location Service Map `arn:aws:geo:eu-west-1:418155680583:map/aircraft-data` as well as a Cognito Identity Pool `arn:aws:cognito-identity:eu-west-1:418155680583:identitypool/eu-west-1:d052d9d8-8b6d-4154-aef4-968d084f2fc0` in my own account.

In the future, I plan to include those resources inside the CDK script.

## 3 Demo

To run our demo, we will start our programs. Both programs will be send to the background, so we keep control over the terminal window.

```sh
~/dump1090/dump1090 --aggressive --net --quiet &
python3 ~/dump1090-to-sqs.py &
```

Our serverless AWS architecture is always online and doesn't have to be started. Simply go to the CloudFront url to visit the website.

# 4 Design considerations

## 4.1 Ingestion

The Raspberry Pi sends data to AWS for ingestion. There are a number of services to consider for this task.

### 4.1.1 Direct invocation

Our Raspberry Pi could directly insert data into our data source. However, if there was a temporary disruption in that service, messages would be lost. Instead, we want to have a buffer between our Raspberry Pi and our data store.

### 4.1.2 Amazon Kinesis Data Streams

Data Streams was used by the demo of Wouter Liefting (see intro). However, this service is billed by the (shard) hour. This would mean that we incur cost even if our Raspberry Pi is turned off and not sending data to be ingested. Therefore, we looked for a serverless service instead.

### 4.1.3 Amazon Kinesis Data Firehose

Firehose is serverless and therfore billed per GB processed. However, Firehose will buffer for at least 60 seconds or 1 MiB (whichever comes first). Since we want updates every second, we will look for another service.

### 4.1.4 Amazon SQS

SQS ticks all the boxes: serverless and fast. The only trade-off is that messages are not guaranteed to be delivered in order. This is fine as long as our message processing is idempotent. Luckily the ADS-B messages contain a timestamp. We can use the [ConditionExpression](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_UpdateItem.html#DDB-UpdateItem-request-ConditionExpression) of DynamoDB UpdateItem to ensure we only update an item if the timestamp is newer than the last update.

## 4.2 Data store

Currently we use DynamoDB as our datastore, however we could look into switching to Amazon Aurora Serverless,
Amazon DocumentDB, Amazon Timestream or Amazon Location Service Trackers.

This is something we would like to revisit in the future.

## 4.3 Static website

Our demo uses a static website with some HTML, JavaScript and YAML files. There are a few approaches to host this website.

### 4.3.1 Amazon S3
A common approach is to make the Amazon S3 bucket public. However, this is discouraged. Most companies are using the [Amazon S3 block public access](https://docs.aws.amazon.com/AmazonS3/latest/dev/access-control-block-public-access.html) functionality to avoid accidentally making any bucket in their account public.

### 4.3.2 Amazon CloudFront

With the combination of a [Amazon CloudFront](https://aws.amazon.com/cloudfront/) dstribution, CloudFront [origin access identity](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html) and an S3 bucket policy, it is possible to serve a private S3 bucket to the public. An added benefit is that CloudFront can also serve requests to our API gatewat under the same domain (avoiding the need for CORS headers) and the capability of caching static files at edge locations for lower latency.

## 4.4 Map service

Lastly, we need a map to draw the aircrafts on.

### 4.4.1 Google Maps

A common tool is [Google Maps JavaScript API](https://developers.google.com/maps/documentation/javascript/overview). However, this is outside the scope of AWS and therefore needs separate access management and provisioning.

### 4.4.2 Amazon Location Service

At re:Invent 2020, AWS announced [Amazon Location Service](https://aws.amazon.com/location/). The service is currently in preview, but is a perfect match for our use case. It is missing CloudFormation support (see 2.3), but when this support is added we can update our demo.

Note that Amazon Location [supports](https://docs.aws.amazon.com/location/latest/developerguide/tutorial-mapbox-gl-js.html#tutorial-mapbox-js-add-dependencies) open source versions of Mapbox GL JS (v1.13.0 or earlier). Starting from [v2.0.0](https://github.com/mapbox/mapbox-gl-js/releases/tag/v2.0.0) Mapbox GL JS is no longer open source.

Therefore this demo uses [Tangram](https://tangrams.readthedocs.io/en/master/) instead.
