#!/usr/bin/env python

import datetime
import joblib
import json
import keras
import logging.config
import math
import numpy as np
import operator
import os
import pandas as pd
import re

from es_pandas import es_pandas
from kafka import KafkaConsumer, KafkaProducer
from keras.models import load_model

from models import config as cfg

logging.config.fileConfig('conf/logging.conf')
logger = logging.getLogger(__name__)

transformations = {
    'diff': {
        'f': operator.sub,
        'f-1': operator.add
    },
    'perc': {
        'f': operator.truediv,
        'f-1': operator.mul
    },
    'log': {
        'f': lambda x,y: np.log(x)-np.log(y),
        'f-1': lambda x,y: np.exp(y)*x,
    }
}

def transform(df, k, t=transformations['diff']):
    if isinstance(df, pd.DataFrame):
        return t['f'](df[k:],df[:-k].values)
    else:
        return t['f'](df[k:],df[:-k])

def inverse_transform(pred, prev, t=transformations['diff']):
    if isinstance(df, pd.DataFrame):
        return t['f-1'](prev.values, pred)
    else:
        return t['f-1'](prev, pred)

MODEL_NAME = 'data_train-seq-12'

MODEL_CFG = cfg.models[MODEL_NAME]
KAFKA_CFG = MODEL_CFG['data']['kafka']
MODEL_FILE = os.path.join('models', MODEL_NAME, MODEL_CFG['file'])
SCALER_FILE = os.path.join('models', MODEL_NAME, MODEL_CFG['scaler'])

consumer = KafkaConsumer(
    KAFKA_CFG['topics']['in'],
    bootstrap_servers=KAFKA_CFG['bootstrap_servers']['in'],
    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
)
logger.info('consuming \'%s\' messages from: %s' % (KAFKA_CFG['topics']['in'], KAFKA_CFG['bootstrap_servers']['in']))

producer = KafkaProducer(
    bootstrap_servers=KAFKA_CFG['bootstrap_servers']['out'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)
logger.info('producing \'%s\' messages to: %s' % (KAFKA_CFG['topics']['out'], KAFKA_CFG['bootstrap_servers']['in']))

def load_model(model_file, scaler_file):
    model = keras.models.load_model(model_file)
    scaler = joblib.load(scaler_file)
    return model, scaler

# ep = es_pandas(cfg.elasticsearch['host'])
# logger.info('elastic stack on: %s' % cfg.elasticsearch['host'])


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

MODEL,SCALER = load_model(MODEL_FILE, SCALER_FILE)
buffer = pd.DataFrame([], columns=MODEL_CFG['data']['in']['columns'])

stripped_beg = False
for message in consumer:
    protocol = message.key.decode('ascii')
    df = pd.read_json(message.value, orient='index')
    df.set_index(MODEL_CFG['data']['in']['index'], inplace=True)
    cols = [col for col in df if col in MODEL_CFG['data']['in']['columns']]
    df = df[cols]
    if df.empty: continue
    buffer = buffer.combine_first(df)
    if not stripped_beg and len(buffer.index) > 1 and buffer.iloc[[0]].isnull().values.any():
        buffer = buffer[1:]
        stripped_beg = True
    if len(buffer.index) > 12 and not (buffer[-1:].isnull().values.any()):
         display(buffer[-12:])