# Network Security AIOps for Online Stream Data Monitoring
This repository contains the source code for the corresponding [**paper**](https://doi.org/10.1007/s00521-024-09863-z).


## DEPMODS - Deployment of MODS alias MODS-aiops

### 1. Clone MODS2 repository

```shell
$ git clone https://github.com/Stifo/mods2.git
$ cd mods2
$ export MODS2_HOME=$(pwd)
```

Create empty certs directory and update permissions.

```shell
cd ${MODS2_HOME}
mkdir nginx/certs
chmod 700 certs
```

Set vm.max_map_count to at least 262144 ([read more](https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html#_set_vm_max_map_count_to_at_least_262144)).

```shell
sysctl -w vm.max_map_count=262144
```

### 2. Create nginx users
Create users in nginx in order to gain access to the proxied services through the proxy server.

#### 2.1 Prerequisities
```shell
$ sudo apt-get install apache2-utils
```

#### 2.2 Create new user

```shell
$ cd ${MODS2_HOME}
$ htpasswd ./nginx/config/.htpasswd [username]
```

### 3. Stack startup
The following command with start the MODS2 stack with all the required services except the log producer. Log producer need to be deployed separately on the log server side. See [Step 4]([4]) how to deploy log producer.

```shell
$ cd ${MODS2_HOME}
$ docker-compose up -d
```
#### 3.1 Check the status of the services
```shell
$ cd ${MODS2_HOME}
$ docker-compose ps
  Name                 Command               State                    Ports                  
---------------------------------------------------------------------------------------------
elastic     /bin/tini -- /usr/local/bi ...   Up      127.0.0.1:9200->9200/tcp, 9300/tcp      
kafka       start-kafka.sh                   Up      0.0.0.0:9092->9092/tcp                  
kibana      /bin/tini -- /usr/local/bi ...   Up      5601/tcp                                
mods2       python manage.py runserver ...   Up                                              
mods2_db    docker-entrypoint.sh postgres    Up      5432/tcp                                
reverse     /docker-entrypoint.sh ngin ...   Up      0.0.0.0:443->443/tcp, 0.0.0.0:80->80/tcp
zookeeper   /bin/sh -c /usr/sbin/sshd  ...   Up      2181/tcp, 22/tcp, 2888/tcp, 3888/tcp
```

#### 3.2 Public IP address of the Kafka service
You should mark down the public IP address of the machine, where you have just deployed MODS2. You will need it later to specify it for the log producer in [Step 4]([4]).

### 4. Log producer deployment
Log producer runs on the log server side and produces log messages to Kafka. Log producer depends on Kafka. Prior the log producer execution, Kafka should be up and running. Kafka is deployed in [Step 3]([3]). Log producer code can be found in the `$MODS2_HOME/tools/logserver` directory.

#### 4.1 Copy the log producer code on the log server
```shell
$ export MODS2_LOGSERVER_IP=XXX.XXX.XXX.XXX
$ scp -r $MODS2_HOME/tools/logserver ${MODS2_LOGSERVER_IP}:~/
```

#### 4.2 Log in to log server
```shell
$ ssh ${MODS2_LOGSERVER_IP}
$ cd ~/logserver
$ export MODS2_LOGSERVER=$(pwd)
```

#### 4.3 Deploy the log producer code
Follow the [log producer documentation](https://nas.dlugolinsky.com:30443/deep/mods2/-/tree/master/tools/logserver/README.md) on how to deploy the log producer code. After the log producer is deployed, it feeds Kafka with zeek/bro log messages from all the monitored files. These log messages appear in the `mods` Kafka channel.

### 5. Log aggregator
Now it's time to deploy log aggregator on the MODS2 Stack side. Log aggregator consumes all the log messages from the 'mods' Kafka channel and aggregates them on 10m interval. Return to the MODS2 Stack shell, navigate to `${MODS2_HOME}/tools/kafka-services` directory and execute the aggregator.

#### 5.1 Start the log aggregator
```shell
$ cd ${MODS2_HOME}/tools/kafka-services
$ ./consumer.sh
```

#### 5.2 Check the log aggregator is running
```shell
$ tail -f logs/consumer.log
2021-05-06 14:18:19,944 - __main__ - INFO - messages processed: 352k
2021-05-06 14:18:38,907 - __main__ - INFO - messages processed: 353k
2021-05-06 14:18:57,930 - __main__ - INFO - messages processed: 354k
2021-05-06 14:19:21,962 - __main__ - INFO - messages processed: 355k
```

### 6. Execute online prediction model
Start jupyter-lab in `${MODS2}/tools/kafka-services/mods_models` directory and execute `train-online.ipynb` notebook.

### 7. Configure Kibana to visualize MODS logs
Open [Kibana's index patterns page](http://127.0.0.1/kibana/app/management/kibana/indexPatterns) in the browser. You have to use username and password created earlier in [Step 2.2]([2.2]) in order to access this page. Click on [+ Create index pattern'](http://127.0.0.1/kibana/app/management/kibana/indexPatterns/create) and create new index pattern named `mods-10m*`. Create [new dashboard](http://127.0.0.1/kibana/app/dashboards#/create) and add lenses to it. Follow Kibana documentation. Share the created dashboard as an `EMBED CODE` of iframe and put this code in `${MODS2_HOME}/mods2/live_monitor/templates/live_monitor_10m.html` template.


### 8. Deployed MODS2
After all these steps are done correctly, you should see current status and prediction in [Live monitor](http://127.0.0.1/mods2/live_monitor/10m) window. The predictions will appear after 10m X model steps.

## Links
- [Elasticsearch interface](http://127.0.0.1/elastic/)
- [Kibana interface](http://127.0.0.1/kibana/)
- [Live monitor](http://127.0.0.1/mods2/live_monitor/10m)

## Important notes
- Kafka is not yet hidden behind the nginx proxy. It has publicly exposed port :9092, thus it requires protection.
- There is just a single Kafka node running yet.
- There is only a single instance of log producer supported yet. Runing additional instance of the log producer will cause log duplicity, which is undesirable.

## Debug

### Kafka
```shell
$ docker run -it --rm edenhill/kafkacat:1.7.0-PRE1 kafkacat -C -b XXX.XXX.XXX.XXX:9093 -t mods-agg-10m
```

## Citation

```
@article{gnsd2024network,
  title={Network security AIOps for online stream data monitoring},
  author={Nguyen, Giang and Dlugolinsky, Stefan and Tran, Viet and L{\'o}pez Garc{\'\i}a, {\'A}lvaro},
  journal={Neural Computing and Applications},
  pages={1--25},
  year={2024},
  publisher={Springer},
  doi={10.1007/s00521-024-09863-z},
  note={CC BY 4.0}
}
```
