# Log server deployment

This is the code to deploy on the side of the log server in order to pass logs to Kafka.

## 1. Prerequisities

* Log server side
  * [Zeek](https://zeek.org/) is running on the log server and producing log files
  * [kafka-python](https://github.com/dpkp/kafka-python)
    ```shell
    pip install -r requirements.txt
    ```
* MODS2 stack is up and running

## 2. adjust the default configuration
Replace the default IP address `147.213.65.206` in `producer.sh` with the public IP address of the machine, where MODS2 Stack is deployed.
```shell
$ export MODS2_IP=127.0.0.1
$ sed -i -E 's/(--bootstrap-servers '"'"')[^:]+(:9092'"'"')/\1'${MODS2_IP}'\2/g' producer.sh
```

## 3. execution
Start the log producer. **ONLY ONE instance pres MODS2 stack is currently supported!!!**
```shell
nohup ./producer.sh &
```

## producer.sh
This is a helper script to execute multiple log parsers and producers (`producer.py`). This script automatically parses log headers. Edit the `logs_dir` and `protocols` variables for adjustments; e.g.:

```shell
logs_dir="/storage/bro/logs/current"
protocols=('conn' 'http' 'dns' 'http' 'sip' 'ssh' 'ssl')
```

The `producer.sh` relies on `tail -F` command, which is equivalent to `--follow=name --retry`.

## producer.py

This is the main log parser and Kafka producer. If the `duration` column is present, this script computes the `ts_end` timestamp as `ts + duration`. Otherwise, if the `duration` column is not present, `ts_end` is set to `ts`. 

### parsing rules
* empty lines and lines beginning with `#` are skipped
* passed lines are spit by `tab`
* default value of the `duration` column is `0.0`

### arguments

**--bootstrap-servers** - a list of Kafka bootstrap servers \
**--channel** - Kafka topic where the message will be published \
**--header** - a list of column names \
**--key** - key used to partition messages (see [more](https://kafka-python.readthedocs.io/en/master/apidoc/KafkaProducer.html#kafka.KafkaProducer.send)) 

## ToDo's

* [ ] securing the communication between producer and Kafka brokers
