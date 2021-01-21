#!/bin/sh

get_output() {
  aws cloudformation describe-stacks \
    --stack-name "AircraftData" \
    --region "eu-west-1" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" \
    --output text
}

queue_url=$(get_output "QueueUrl")
key_id=$(get_output "AccessKeyId")
secret=$(get_output "SecretAccessKey")
region=$(get_output "Region")

echo "export QUEUE_URL='$queue_url'"
echo "aws configure set aws_access_key_id '$key_id'"
echo "aws configure set aws_secret_access_key '$secret'"
echo "aws configure set region '$region'"
