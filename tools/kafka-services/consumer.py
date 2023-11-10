#!/usr/bin/env python

import datetime
import json
import logging.config
import math
import re
import sys

import pandas as pd
from es_pandas import es_pandas
from kafka import KafkaConsumer, KafkaProducer
from tzlocal import get_localzone

from conf import consumer as cfg

logging.config.fileConfig('conf/logging.conf')
logger = logging.getLogger('mods2')

logger.info('cfg.kafka: %s' % cfg.kafka)
logger.info('distillation_rules: %s' % cfg.distillation_rules)

def str2bytes(s):
    if sys.version_info < (3, 0):
        return bytes(s)
    return bytes(s, 'utf8')

consumer = KafkaConsumer(
    cfg.kafka['topics']['in'],
    bootstrap_servers=cfg.kafka['bootstrap_servers']['in'],
    key_deserializer=lambda k: k,
    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
)
logger.info('consuming \'%s\' messages from: %s' % (cfg.kafka['topics']['in'], cfg.kafka['bootstrap_servers']['in']))

producer = KafkaProducer(
    bootstrap_servers=cfg.kafka['bootstrap_servers']['out'],
    key_serializer=lambda k: str2bytes(k),
    value_serializer=lambda v: str2bytes(json.dumps(v))
)
logger.info('producing \'%s\' messages to: %s' % (cfg.kafka['topics']['out'], cfg.kafka['bootstrap_servers']['in']))

ep = es_pandas(cfg.elasticsearch['host'])
logger.info('elastic stack on: %s' % cfg.elasticsearch['host'])

DIRECTION_IN = 'in'
DIRECTION_OUT = 'out'
DIRECTION_INTERNAL = 'internal'


def net_direction(orig_h, resp_h, regex_local):
    if re.match(regex_local, orig_h):
        if re.match(regex_local, resp_h):
            return DIRECTION_INTERNAL
        else:
            return DIRECTION_OUT
    else:
        return DIRECTION_IN


def add_direction(df):
    if cfg.net_direction['orig_field'] in df.columns and cfg.net_direction['resp_field'] in df.columns:
        logger.debug('add_direction call: %s' % df)
        df[cfg.net_direction['field_name']] = df.apply(
            lambda row: net_direction(
                row[cfg.net_direction['orig_field']],
                row[cfg.net_direction['resp_field']],
                cfg.net_direction['regex']
            ),
            axis=1
        )
        logger.debug('add_direction result: %s' % df)
    return df


#
# extracts only necessary data from the message
#
def distill(message, fields):
    distilled = []
    for f in fields:
        distilled.append(message.value[f])
    return distilled


#
# computes time window for time t; i.e., <begin, end)
#
def epoch(t, period):
    days = period.days
    hours = math.floor(period.seconds / 3600)
    minutes = math.floor((period.seconds % 3600) / 60)
    seconds = period.seconds % 60
    beg = t - datetime.timedelta(
        days=t.day % days if days > 0 else 0,
        hours=t.hour % hours if hours > 0 else 0,
        minutes=t.minute % minutes if minutes > 0 else 0,
        seconds=t.second % seconds if seconds > 0 else t.second,
        microseconds=t.microsecond
    )
    end = beg + period
    return beg, end


#
# cleans data and sets dtype
#
def clean(df, rules):
    for errors, columns in rules['to_numeric'].items():
        df[columns] = df[columns].apply(pd.to_numeric, errors=errors)
    for fill, columns in rules['fillna'].items():
        df[columns] = df[columns].fillna(fill)
    for t, columns in rules['astype'].items():
        df[columns] = df[columns].astype(t)
    return df


def vectorizedf(df, prefix=''):
    logger.debug('vectorized, df: %s, prefix: %s' % (df, prefix))
    while not isinstance(df, pd.Series):
        df = df.stack().swaplevel()
    df.index = df.index.map(lambda x: '_'.join(x))
    df.index = df.index.map(('%s{0}' % prefix).format)
    logger.debug(df)
    return df.to_frame().T.sort_index(1, 1)


#
# aggregates buffered message data according to given rules
#
def aggregate(buf, protocol):
    col_prefix = '%s_' % protocol
    columns = cfg.distillation_rules[protocol]
    df = pd.DataFrame(buf, columns=columns)

    # resolve network direction
    df = add_direction(df)
    if protocol in cfg.data_cleaning_rules.keys():
        df = clean(df, cfg.data_cleaning_rules[protocol])

    # add grouping by networking direction field
    net_dir_grp = cfg.net_direction['field_name'] in df.columns

    # 1-level agg
    df_agg1 = pd.DataFrame()
    if protocol in cfg.aggregation_rules['agg']:
        df_agg1 = (df.groupby(cfg.net_direction['field_name']) if net_dir_grp else df) \
            .agg(cfg.aggregation_rules['agg'][protocol])
        df_agg1 = vectorizedf(df_agg1, prefix=col_prefix)

    # 2-level agg
    df_agg2 = pd.DataFrame()
    if protocol in cfg.aggregation_rules['groupby']:
        gb_rules = cfg.aggregation_rules['groupby'][protocol]
        for gb, agg in gb_rules.items():
            tmp = df.groupby([cfg.net_direction['field_name'], gb] if net_dir_grp else gb).agg({gb: agg}).T
            df_agg2 = df_agg2.append(tmp)
            df_agg2 = df_agg2.fillna(0)
        df_agg2 = vectorizedf(df_agg2, prefix=col_prefix)

    # join columns and sort
    df_agg = df_agg1.join(df_agg2).sort_index(1, 1)
    return df_agg


tz_local = get_localzone()

logger.debug('local timezone: %s' % tz_local)

buffer = {}
counter = 0

for message in consumer:

    #logger.debug(message)

    counter += 1
    if counter % 1000 == 0:
        logger.info('messages processed: %dk' % (counter / 1000))

    protocol = message.key.decode('utf8')

    if protocol not in cfg.distillation_rules.keys():
        continue

    logger.debug(message)

    now = datetime.datetime.now(tz_local)
    msg_dt = datetime.datetime.fromtimestamp(message.timestamp * 1e-6, tz=tz_local)
    msg_epoch = epoch(msg_dt, cfg.aggregation_period)

    logger.debug('now: %s\tmsg_dt: %s\tmsg_epoch: %s' % (now, msg_dt, msg_epoch))

    diff = now - msg_epoch[1]
    if diff <= cfg.aggregation_period:
        if protocol not in buffer.keys():
            buffer[protocol] = {}
        if msg_epoch not in buffer[protocol].keys():
            buffer[protocol][msg_epoch] = []
        distilled = distill(message, cfg.distillation_rules[protocol])
        buffer[protocol][msg_epoch].append(distilled)

    for p in list(buffer):
        for key in list(buffer[p]):
            if now - key[1] > cfg.aggregation_period:
                df_agg = aggregate(buffer[p][key], p)
                index = pd.Index([key[1]], name='ts')
                df_agg = df_agg.set_index(index)
                df_agg.reset_index(level=0, inplace=True)
                logger.debug('aggregated df: %s' % df_agg)
                logger.info('sending aggregated data to index: [%s][%s][%s]' % (cfg.elasticsearch['index'], p, key))
                data_written = ep.to_es(
                    df_agg,
                    cfg.elasticsearch['index'],
                    use_pandas_json=True,
                    doc_type='log',
                    use_index=False
                )
                logger.info('%d doc%s sucessfully written to index' % (data_written, '' if data_written == 1 else 's'))
                df_json = df_agg.to_json(orient='index')
                logger.debug('df_json: %s' % df_json)
                logger.info(
                    'sending aggregated data to kafka: [%s][%s][%s]' % (cfg.kafka['topics']['out'], p, key))
                producer.send(
                    topic=cfg.kafka['topics']['out'],
                    key=p,
                    value=df_json
                )
                del buffer[p][key]
