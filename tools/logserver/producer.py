#!/bin/sh
''''exec python -u -- "$0" ${1+"$@"} # '''
# vi: syntax=python

#
# get header from file:
#
# sed '7q;d' ~/logs/current/conn.log
#

import argparse
import datetime
import json
import logging.config
import pytz
import re
import sys

from kafka import KafkaProducer
from kafka.cluster import ClusterMetadata
from kafka.errors import KafkaError
from tzlocal import get_localzone

logging.config.fileConfig('conf/logging.conf')
logger = logging.getLogger('mods2')

parser = argparse.ArgumentParser(description='log producer')
parser.add_argument('--bootstrap-servers', nargs='+',
                    help='one or more Kafka bootstrap servers in the format HOST:PORT', required=True)
parser.add_argument('--key', help='message key', required=True)
parser.add_argument('--header', nargs='+', help='message header', required=True)
parser.add_argument('--channel', help='output channel name', required=True)

tz_local = get_localzone()
logger.debug('local timezone: %s' % tz_local)

def str2bytes(s):
    if sys.version_info < (3, 0):
        return bytes(s)
    return bytes(s, 'utf8')

args = parser.parse_args()
logger.info('starting producer: %s' % args)
producer = KafkaProducer(
    bootstrap_servers=args.bootstrap_servers,
    key_serializer=lambda k: str2bytes(k),
    value_serializer=lambda v: str2bytes(json.dumps(v))
)

logger.info('bootstrap_connected: %s' % producer.bootstrap_connected())

def parse_duration(duration):
    try:
        return float(duration)
    except ValueError:
        return 0.0

def totimestampmicro(dt, epoch=datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)):
    td = dt - epoch
    return (td.microseconds + (td.seconds + td.days * 86400) * 10**6)

def on_send_success(record_metadata):
    logger.debug(record_metadata)
#    logger.debug(record_metadata.topic)
#    logger.debug(record_metadata.partition)
#    logger.debug(record_metadata.offset)

def on_send_error(excp):
    logger.error('failed to send data to kafka', exc_info=excp)


while True:

    line = sys.stdin.readline()

    if not line: break
    if line.startswith('#'): continue
    if len(line) == 0: continue

    line = line.rstrip("\n")

    data = re.split(r'\t', line)

    if len(data) < len(args.header):
        logger.warning(
            'Incomplete line detected! len(data)=%d, len(args.header)=%d, line=' % (len(data), len(args.header), line))
        prev_line = line
        continue

    data_json = {}
    for i, k in enumerate(args.header):
        data_json[k] = data[i]

    ts_end = float(data_json['ts'])
    if 'duration' in data_json.keys():
        duration = parse_duration(data_json['duration'])
        ts_end += duration

    # code to resolve timezone and UTC timestamp
    # here, the data_json['ts'] is already in UTC, so we skip it
    #ts_end_tmp = ts_end
    #dt_end = datetime.datetime.fromtimestamp(ts_end)
    #dt_end = tz_local.localize(dt_end)
    #ts_end = totimestampmicro(dt_end)
    
    ts_end = int(ts_end * 1e6)
    data_json['ts_end'] = ts_end

    producer\
    .send(
        topic=args.channel,
        key=args.key,
        value=data_json,
        timestamp_ms=ts_end
    )\
    .add_callback(on_send_success)\
    .add_errback(on_send_error)
