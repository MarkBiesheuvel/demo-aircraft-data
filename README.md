# Demo: Real-time aircraft data ingestion to AWS

This demo uses a [Raspberry Pi](https://www.raspberrypi.org/) and [RTL-SDR](https://www.rtl-sdr.com/) dongle to receive ADS-B messages. These messages are broadcast by aircrafts on 1090 MHz. To decode the signal the Raspberry Pi runs a program called [dump1090](https://www.satsignal.eu/raspberry-pi/dump1090.html). This program makes the message available on port 30003 by default. Therefore, we run a Python script that listens on that port, transforms the message to JSON and forwards this to [AWS SQS](https://aws.amazon.com/sqs/).

## 1. Setup: Raspberry Pi

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

### 1.4 Get Python code of demo

Download the sync python script.

```sh
wget -q -O ~/dump1090-to-sqs.py https://raw.githubusercontent.com/MarkBiesheuvel/demo-aircraft-data/master/scripts/dump1090-to-sqs.py
python3 -m pip install boto3
```


## 2 Deploying the AWS infrastructure

To deploy the AWS infrastructure we will use the AWS Cloud Development Kit (CDK).

```sh
sudo npm install -g aws-cdk --update
python3 -m pip install -r cdk/requirements.txt
cdk deploy
```

Next, configure the queue url, region, and access key and secret in on the Raspberry Pi.

```sh
export QUEUE_URL=
aws configure
```

## 3 Run the programs

Lastly we will start our programs. Both programs will be send to the background.

```sh
~/dump1090/dump1090 --aggressive --net --quiet &
python3 ~/dump1090-to-sqs.py &
```
