# AWS Configuration

### Configure AWS IoT CLI to get access to IoT

To install AWS CLI ([Reference](http://docs.aws.amazon.com/es_es/cli/latest/userguide/installing.html#install-bundle-other-os)):

```bash
$ curl "https://s3.amazonaws.com/aws-cli/awscli-bundle.zip" -o "awscli-bundle.zip"
$ unzip awscli-bundle.zip
$ sudo ./awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws
```

Test installation:

```bash
aws help
```

To create access keys([Reference](http://docs.aws.amazon.com/es_es/AWSSimpleQueueService/latest/SQSGettingStartedGuide/AWSCredentials.html)):

 - Open the IAM console.
 - In the navigation pane, choose Users.
 - Choose your IAM user name (not the check box).
 - Choose the Security Credentials tab and then choose Create Access Key.
 - To see your access key, choose Show User Security Credentials. Your credentials will look something like this:

```
Access Key ID: AKIAIOSFODNN7EXAMPLE
Secret Access Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Choose Download Credentials, and store the keys in a secure location.
```

Configure the AWS CLI:

```bash
$ aws configure
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: eu-west-1
Default output format [None]:
```

Give the user permissions for AWS IoT, that is done by attach to him AWSIoTFullAccess policy under Users permission tab. After that user can check devices in AWS:

```
aws iot list-things
```


### Create a device in AWS IoT ([reference](https://www.hackster.io/mariocannistra/python-and-paho-for-mqtt-with-aws-iot-921e41))


```bash
$ aws iot create-thing --thing-name "sim_02"
{
    "thingArn": "arn:aws:iot:eu-west-1:111111111111:thing/device",
    "thingName": "device"
}
```

Create device keys:

```bash
aws iot create-keys-and-certificate --set-as-active --certificate-pem-outfile cert.pem --public-key-outfile publicKey.pem --private-key-outfile privkey.pem
```

A list of certificates can be seen on:

```
aws iot list-certificates
```

Download root certificate from [this URL](https://www.symantec.com/content/en/us/enterprise/verisign/roots/VeriSign-Class%203-Public-Primary-Certification-Authority-G5.pem) using your browser and save it with filename: aws-iot-rootCA.crt.

Create a policy document (iotpolicy.json) that contains:

```json
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action":["iot:*"],
        "Resource": ["*"]
    }]
}
```

Create a policy from the file created:

```bash
$ aws iot create-policy --policy-name "PubSubToAnyTopic" --policy-document file://iotpolicy.json
{
    "policyName": "PubSubToAnyTopic",
    "policyArn": "arn:aws:iot:eu-west-1:111111111111:policy/PubSubToAnyTopic",
    "policyDocument": "{\n    \"Version\": \"2012-10-17\", \n    \"Statement\": [{\n        \"Effect\": \"Allow\",\n        \"Action\":[\"iot:*\"],\n        \"Resource\": [\"*\"]\n    }]\n}\n",
    "policyVersionId": "1"
}

```

Attach the policy using previous *certificate-arn* field:

```
aws iot attach-principal-policy --principal "certificate-arn" --policy-name "PubSubToAnyTopic"
```

To get the endpoint configuration:

```
$ aws iot describe-endpoint
{
    "endpointAddress": "A2KYAWFNYZAAAA.iot.eu-west-1.amazonaws.com"
}
```

Attach certificate to the device:

```bash
aws iot attach-thing-principal --thing-name "device" --principal "certificate-arn"
```


### Configure rules ([reference](http://docs.aws.amazon.com/es_es/iot/latest/developerguide/config-and-test-rules.html))

Create an IAM role that AWS IoT can assume to perform actions when rules are triggered. Save the following Assume Role policy document (that is, trust relationship) to the file role_policy.json:

```bash
{
"Version": "2012-10-17",
"Statement": [{
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
            "Service": "iot.amazonaws.com"
       },
      "Action": "sts:AssumeRole"
  }]
}
```

Give the user permissions for AWS IoT, that is done by attach to him AdministratorAccess policy under Users permission tab.b To create the IAM (Identity and Access Management) role, run the create-role command, passing in the Assume Role policy document:

```bash
$ aws iam create-role --role-name iot-actions-role --assume-role-policy-document file://path-to-file/role_policy.json
{
    "Role": {
        "AssumeRolePolicyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {
                        "Service": "iot.amazonaws.com"
                    },
                    "Effect": "Allow",
                    "Sid": ""
                }
            ]
        },
        "RoleId": "AROAJND6WOTIONSAAAAA",
        "CreateDate": "2016-04-17T20:43:42.264Z",
        "RoleName": "iot-actions-role",
        "Path": "/",
        "Arn": "arn:aws:iam::111111111111:role/iot-actions-role"
    }
}
```

To grant permissions to the role, save this policy to the file role_permissions.json:

```bash
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": [ "dynamodb:*", "lambda:InvokeFunction"],
        "Resource": ["*"]
    }]
}
```

Call create-policy and specify it:

```bash
$ aws iam create-policy --policy-name iot-actions-policy --policy-document file:///path-to-file/role_permissions.json
{
    "Policy": {
        "PolicyName": "iot-actions-policy",
        "CreateDate": "2016-04-17T20:51:01.873Z",
        "AttachmentCount": 0,
        "IsAttachable": true,
        "PolicyId": "ANPAINOPO545JVAIAAAAA",
        "DefaultVersionId": "v1",
        "Path": "/",
        "Arn": "arn:aws:iam::111111111111:policy/iot-actions-policy",
        "UpdateDate": "2016-04-17T20:51:01.873Z"
    }
}
```

Attach policy to the role:

```bash
aws iam attach-role-policy --role-name iot-actions-role --policy-arn "arn:aws:iam::111111111111:policy/iot-actions-policy"
```

#### Create a rule

From [DynamoDB console](https://console.aws.amazon.com/dynamodb/home) create DynamoDB table with a partition key of type string and a sort key of type string.

Create a json file (dynamo__iot_rule.json) to create the rule:

```bash
{
  "sql": "SELECT * FROM '#'",
  "ruleDisabled": false,
  "actions": [{
      "dynamoDB": {
        "tableName": "IoT_data",
        "hashKeyField": "partition_key",
        "hashKeyValue": "${topic()}",
        "rangeKeyField": "timestamp",
        "rangeKeyValue": "${timestamp()}",
        "roleArn": "arn:aws:iam::111111111111:role/iot-actions-role"
      }
    }]
}
```

Create the rule:

```bash
aws iot create-topic-rule --rule-name saveToDynamoDB --topic-rule-payload file://path-to-file/dynamo_iot_rule.json
```
