# Cloud connector installation guide

## Install prerequisites

Install system prerequisites:

Requires Python > 2.7.9. Version 3 is not supported by coap library and tls v1.2 is only supported for > 2.7.9.

```bash
sudo apt-get update
sudo apt-get install python-pip python-dev
```

Install application libraries:

```bash
sudo pip install -r requirements.txt
```

## Configuration
In the folder *cloud_connector* use the file *config.yml* to configure the application. There are sections for device, tsdb and cloud

### Device
Only OpenMote devices supported at this moment.

To configure the devices, there should be a read interval (in seconds) and for each device the ipv6 address ana a name
```yaml
devices:
  read_interval: 5
  mote01:
    name: mote01
    ipv6: bbbb::12:4b00:0615:aaaa
```

### TSDB
Only InfluxDB supported.

Configure parameters for influxDB, like the following example:

```yaml
tsdb:
  influxdb:
    host: 192.168.1.44
    port: 8086
    user: root
    password: root
    database: iot_values
```

### Cloud
Supported cloud services are AWS IoT, thethings.iO and PubNub.

Each service is configure by it's name if its used: aws, pubnub, thethingsio. There is no need to configure all the services, only one can be configured. The parameters are different depending the cloud configuration parameters.

Also an strategy should be configure for each cloud service.

#### AWS IoT

```yaml
cloud:
  aws:
    host: A2KYAWFNAAAAAA.iot.eu-west-1.amazonaws.com
    port: 8883
    ca_path: ../keys/aws-iot-rootCA.crt
    cert_path: ../keys/cert.pem
    key_path: ../keys/privkey.pem
```

#### thethings.iO

There need one token for each device, the key of the token must match the device name defined on devices.

```yaml
cloud:
  thethingsio:
    tokens:
      mote01: l0M5BEaDdzt40VqGy6omEqZyDY62CxA6XwCJixxxxxx
```

#### PubNub

```yaml
cloud:
  pubnub:
    publish_key: pub-c-b3d6a6e3-ce77-4a89-9e0b-49e52edddddd
    subscribe_key: sub-c-d74fa040-16f4-11e6-8bc8-0619f89ddddd
```

### Strategies

It's defined for each cloud service, there are different kinds of strategies: All, MessageLimit, TimeLimit, Variation.

- All: Send all messages.
- MessageLimit: Send a limited maximum number of messages per day.
- TimeLimit: Send message only if there has passed some times between the latest one.
- Variation: Only send message if there is a defined variation of a value. It defines a *time_low* below no message is sent, a *time_high* after a message will be sent even if variation threshold has not been reach and *variability* for each value.

```yaml
strategy:
  type: Variation
  parameters:
    time_low: 10
    time_high: 300
    variability:
      temperature: 0.5
      humidity: 2
      light: 5
```

## Execution

Run in cloud_connector folder:

```bash
python ./cloud_connector.py
```
