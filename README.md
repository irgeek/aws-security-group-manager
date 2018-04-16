# AWS Security Group Manager #

### What is this repository for?

An AWS Step Function and Lambda Function to manage temporary security group
ingress entries.

Each time the Step Function state machine is started, a list if IPs and CIDRs
is passed in. The IPs and CIDRs are combined with a list of allowed ingress
ports and security groups are configured to allow access. After a configurable
delay, the entries are removed automatically.

### How do I get set up?

The easiest way to set up the Step Function state machine and Lambda Function
is to create a CloudFormation stack using the `aws-cli` and the included
CloudFormation template. The `package` subcommand creates the Lambda zip file
and uploads it to your S3 bucket. The `deploy` subcommand stands up the actual
stack.

```
aws cloudformation package \
  --s3-bucket <S3_BUCKET> \
  --s3-prefix <S3_PREFIX> \
  --template-file cloudformation.yaml \
  --output-template-file processed.yaml

aws cloudformation deploy \
  --template-file processed.yaml \
  --capabilities CAPABILITY_IAM \
  --stack-name <STACK_NAME>
```

### Ingress Configuration

The Lambda Function looks for an environment variable called `ALLOW_INGRESS` to
get the list of security groups and ports to open up temporarily for each
request. The format is a comma-separated list of entries. Each entry is the
security group Id, protocol and port joined together with colons. The list can
be easily managed in the CloudFormation template.

```
ALLOW_INGRESS: !Join
  - ','
  - - sg-xxxxxxxx:TCP:22
    - sg-yyyyyyyy:TCP:80
```

### Starting the State Machine

The Step Function state maching takes a JSON object as input:

```
{
  "ips": [
    "203.0.113.4",
    "2001:db8::1"
  ],
  "cidrs": [
    "203.0.113.64/26",
    "2001:db8::beef:0/112"
  ],
  "delay": "1h"
}
```

To allow the current public IP of your computer access for two hours, you can
combine the `aws-cli` and `curl` like this:

```
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:<AWS_REGION>:<ACCOUNT_ID>:stateMachine:<STATE_MACHINE_NAME> \
  --input "{\"ips\":[\"$(curl -s 'https://api.ipify.org?format=text')\"],\"delay\":\"2h\"}"
```
