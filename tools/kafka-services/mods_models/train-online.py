#!/bin/sh
''''exec python -u -- "$0" ${1+"$@"} # '''
# vi: syntax=python

import logging.config
logging.config.fileConfig('conf/train-online-logging.conf')
logger = logging.getLogger('mods2')

import datetime
import joblib
import json
import math
import numpy as np
import operator
import os
import pandas as pd
import seaborn as sns
import tensorflow as tf

from es_pandas import es_pandas

from kafka import KafkaConsumer, KafkaProducer
from kafka.structs import TopicPartition

from tensorflow.keras.callbacks import Callback, EarlyStopping, ModelCheckpoint, TensorBoard
from tensorflow.keras.layers import Dense, Dropout, Input, LSTM
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.preprocessing.sequence import TimeseriesGenerator

from numpy import hstack

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, PowerTransformer, QuantileTransformer

from statsmodels.tsa.seasonal import STL

from tensorflow.compat.v1 import ConfigProto
from tensorflow.compat.v1 import InteractiveSession

config = ConfigProto()
config.gpu_options.allow_growth = True
config.gpu_options.per_process_gpu_memory_fraction = 0.1
session = InteractiveSession(config=config)

cfg = {
    'kafka': {
        'bootstrap_servers': {
            'in': ['127.0.0.1:9093', '127.0.0.1:9094', '127.0.0.1:9095'],
            'out': ['127.0.0.1:9093', '127.0.0.1:9094', '127.0.0.1:9095']
        },
        'topics': {
            'in': 'mods-agg-10m',
            'out': 'mods-10m-pred'
        }
    },
#     'model': os.path.join('models', 's24-l6-diff')
    'model': os.path.join('models', 'm2-incr-nostl')
}

buffer_file = os.path.join('tmp', 'buffer')
online_model_file = os.path.join(cfg['model'], 'model-online.h5')

def load_model(model_dir) -> (Model, Pipeline, Pipeline, dict):
    logger.debug('load_model(model_dir=\'%s\')' % model_dir)
    # load cfg
    cfg_file = open(os.path.join(model_dir, 'cfg.json'), 'r')
    cfg = json.load(cfg_file)
    cfg_file.close()
    logger.info('model configuration loaded')
    logger.debug(cfg)
    # load transformation pipelines
    transform_pipeline_X = joblib.load(os.path.join(model_dir, 'sklearn_pipeline_X.pkl'))
    transform_pipeline_Y = joblib.load(os.path.join(model_dir, 'sklearn_pipeline_Y.pkl'))
    # load model
    model = tf.keras.models.load_model(online_model_file if os.path.isfile(online_model_file) else os.path.join(model_dir, 'model.h5'))
    logger.info('model loaded')
    mods2_model = {
        'model': model,
        'transform_pipeline_X': transform_pipeline_X,
        'transform_pipeline_Y': transform_pipeline_Y,
        'cfg': cfg
    }
    return mods2_model


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

# @giang
class GiangTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, cfg, epsilon=1):
        self.epsilon = epsilon
        self.remove_peak = cfg['remove_peak']
        self.test_stl = cfg['test_stl']
        self.stl_period = cfg['stl_period']
        self.isfitted = False
    def fit(self, X):
        if self.remove_peak:
            q_min, q_max = np.percentile(X, [25, 75], axis=0)
            iqr = q_max - q_min
            self.iqr_min = q_min - 1.5*iqr
            self.iqr_max = q_max + 1.5*iqr
        self.isfitted = True
        return self
    def transform(self, X):
        X_ = X.copy()
        if self.test_stl:
            for col in range(X_.shape[1]):
                res = STL(X_[:,col], period=self.stl_period, robust=True).fit()
                X_[:,col] = res.trend + res.seasonal
        if not self.isfitted:
            self.fit(X_)
        if self.remove_peak:
            X_ = np.clip(X_, a_min=self.iqr_min, a_max=self.iqr_max)
        X_ = np.where(X_ < 0, self.epsilon, X_)
        return X_
    def inverse_transform(self, X):
        X_ = X.copy()
        return X_


# load model
mods2_model = load_model(cfg['model'])
mods2_model['cfg']['train']['epochs_incremental'] = 10

logger.info('creating Kafka consumer ...')
consumer = KafkaConsumer(
    cfg['kafka']['topics']['in'],
    bootstrap_servers=cfg['kafka']['bootstrap_servers']['in'],
    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
)

logger.info('es_pandas initialization ...')
ep = es_pandas('127.0.0.1:9200')

def save_buffer(buffer, buffer_file=buffer_file):
    logger.debug('save_buffer(buffer_file=\'%s\', buffer)' % buffer_file)
    buffer.to_csv(buffer_file, sep='\t')

def load_buffer(buffer_file=buffer_file):
    logger.debug('load_buffer(buffer_file=\'%s\'' % buffer_file)
    return pd.read_csv(buffer_file, sep='\t')

def save_model(model, model_file=online_model_file):
    logger.debug('save_model(model, model_file=\'%s\')' % model_file)
    model.save(model_file)

def differentiate(df:pd.DataFrame, k) -> pd.DataFrame:
    return df[k:]-df[:-k].values

def inverse_differentiate(df:pd.DataFrame, seen:pd.DataFrame, k) -> pd.DataFrame:
    return seen.values+df

def transform(mods2_model:dict, df:pd.DataFrame) -> pd.DataFrame:
    isdiff = mods2_model['cfg']['differential']
    if isdiff:
        forecast_steps = mods2_model['cfg']['forecast_steps']
        return differentiate(df, forecast_steps)
    else:
        return df

def inverse_transform(mods2_model:dict, df:pd.DataFrame, df_orig:pd.DataFrame) -> pd.DataFrame:
    isdiff = mods2_model['cfg']['differential']
    if isdiff:
        sequence_length = mods2_model['cfg']['tsg']['length']
        forecast_steps = mods2_model['cfg']['forecast_steps']
        prev = df_orig[-1:].values
        return df + prev
    else:
        return df

def create_tsg(mods2_model, X, Y):
    forecast_steps = mods2_model['cfg']['forecast_steps']
    args = mods2_model['cfg']['tsg']
    if forecast_steps > 1:
        return TimeseriesGenerator(
            X[:-forecast_steps+1],
            Y[forecast_steps-1:],
            **args
        )
    else:
        return TimeseriesGenerator(
            X,
            Y,
            **args
        )

def prepare_data_for_train(
    mods2_model:dict,
    df:pd.DataFrame
):
    features_X = mods2_model['cfg']['data']['X']
    features_Y = mods2_model['cfg']['data']['Y']
    pipeline_X = mods2_model['transform_pipeline_X']
    pipeline_Y = mods2_model['transform_pipeline_Y']
    #
    X = df[features_X]
    X = transform(mods2_model, X)
    X = X.values.astype('float32')
    X = pipeline_X.fit_transform(X)
    Y = df[features_Y]
    Y = transform(mods2_model, Y)
    Y = Y.values.astype('float32')
    Y = pipeline_Y.fit_transform(Y)
    #
    return X,Y

def update_model(mods2_model, data_train):
    # TODO:
    # 1) clone model
    # 2) exec in new thread, while old model keeps running
    # 3) update transformers???
    #
    # Checkpointing and earlystopping
    checkpoints = ModelCheckpoint(
        os.path.join('./checkpoints/lstm-{epoch:02d}.hdf5'),
        monitor='loss',
        save_best_only=True,
        mode='auto',
        verbose=0
    )
    #
    earlystops = EarlyStopping(
        monitor='loss',
        patience=25,
        verbose=0
    )
    #
    callbacks_list = [checkpoints, earlystops]
    #
    X,Y = prepare_data_for_train(
        mods2_model,
        data_train
    )
    tsg_train = create_tsg(
        mods2_model,
        X,
        Y
    )
    model = mods2_model['model']
    for i in range(mods2_model['cfg']['train']['epochs_incremental']):
        print('epoch: %d' % (i+1))
        model.fit(
            tsg_train,
            epochs=1,
            shuffle=False,
            callbacks=callbacks_list,
            batch_size=mods2_model['cfg']['tsg']['batch_size'],
            verbose=1
        )
        model.reset_states()
    save_model(model, online_model_file)

def get_time_step(df):
    step = df.index[-1] - df.index[-2]

def predict(mods2_model, df):
    model = mods2_model['model']
    isdiff = mods2_model['cfg']['differential']
    forecast_steps = mods2_model['cfg']['forecast_steps']
    features_X = mods2_model['cfg']['data']['X']
    features_Y = mods2_model['cfg']['data']['Y']
    pipeline_X = mods2_model['transform_pipeline_X']
    pipeline_Y = mods2_model['transform_pipeline_Y']
    #
    X = df[features_X]
    Y = df[features_Y]
    #
    Xt = transform(mods2_model, X)
    Xt = pipeline_X.transform(Xt.to_numpy())
    #
    Yp = Y[-1:].copy(deep=True)
#     time_delta = forecast_steps * (Y.index[-1] - Y.index[-2])
    time_delta = pd.Timedelta(minutes=10)
    Yp.set_index(Yp.index + time_delta, inplace=True)
    #
    pred = model.predict(Xt[np.newaxis,:], verbose=1, batch_size=1)
    pred = pipeline_Y.inverse_transform(pred)
    Yp[:] = pred
    Yp = inverse_transform(mods2_model, Yp, Y)
    #
    return Yp

# for tp in consumer.assignment():
#     consumer.seek_to_beginning(tp)

# features
features = list(set(mods2_model['cfg']['data']['X'] + mods2_model['cfg']['data']['Y']))
features.sort()

is_differential = mods2_model['cfg']['differential']
context_length = mods2_model['cfg']['tsg']['length'] + (mods2_model['cfg']['forecast_steps'] if is_differential else 0)

# store incomming messages in buffer
buffer = load_buffer(buffer_file) if os.path.isfile(buffer_file) else pd.DataFrame([], columns=features)
stripped_beg = False

logger.info('listening for Kafka messages ...')
num_messages = 0
for message in consumer:
    num_messages+=1
    logger.debug('messages: %d' % num_messages)
    protocol = message.key.decode('ascii')
    df = pd.read_json(message.value, orient='index')
    df.set_index('ts', inplace=True)
    df.index = pd.to_datetime(df.index, unit='ms')
    cols = [col for col in df if col in features]
    df = df[cols]
    if df.empty:
        continue
    buffer = buffer.combine_first(df)
    #
    # interpolate nan
    # buffer[cols] = buffer[buffer[cols].isnull().any().index.values].interpolate(method='time')
    # fill nan with zeroes
    buffer[cols] = buffer[buffer[cols].isnull().any().index.values].fillna(0)
    save_buffer(buffer, buffer_file)
    #
    if not stripped_beg and len(buffer.index) > 1 and buffer.iloc[[0]].isnull().values.any():
        buffer = buffer[1:]
        save_buffer(buffer, buffer_file)
        stripped_beg = True
    if len(buffer.index) >= context_length\
        and (not buffer[-1:].isnull().values.any()):
        XY = buffer[-context_length:]
        Y = predict(mods2_model, XY)
#         Y = Y.tz_localize('Europe/Bratislava')
        Y['model'] = mods2_model['cfg']['model_name']
        Y.reset_index(level=0, inplace=True)
        ep_written = ep.to_es(
            Y,
            cfg['kafka']['topics']['out'],
            use_pandas_json=True,
            doc_type='pred',
            use_index=False
        )
        #
        buffer_len_h = (buffer.index[-1]-buffer.index[0]).total_seconds()/3600
        if buffer_len_h > mods2_model['cfg']['tsg']['length']:
            data_train = buffer
            buffer = buffer[-context_length+1:] # leave previous context for the next prediction
            save_buffer(buffer, buffer_file)
            stripped_beg = False
            update_model(mods2_model, data_train)

