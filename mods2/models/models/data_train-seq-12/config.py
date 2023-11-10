# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
Created on Fri May  4 12:35:11 2018

MODS configuration file

@author: giangnguyen
@author: stefan dlugolinsky
"""

import fnmatch
import os
from os import path
from os.path import expanduser
import html


def list_dir(dir, pattern='*.tsv'):
    listOfFiles = os.listdir(dir)
    tsv_files = []
    for entry in listOfFiles:
        if fnmatch.fnmatch(entry, pattern):
            tsv_files.append(entry)
    return tsv_files


# identify basedir for the package
BASE_DIR = path.dirname(path.normpath(path.dirname(__file__)))

# Data repository
DATA_DIR = expanduser("~") + '/data/deep-dm/'  # app_data_raw

# Data dirs
dir_logs    = DATA_DIR + 'logs/'
dir_parquet = DATA_DIR + 'logs_parquet/'
dir_cleaned = DATA_DIR + 'logs_cleaned/'
log_header_lines = 8

# Feature data in Spark                           # moved Spark out of here?
# feature_filename = 'features.tsv'
# time_range_begin = '2018-04-13'                 # begin <= time_range < end
# time_range_end   = '2019-05-25'                 # excluded
# window_duration = '1 hour'
# slide_duration  = '10 minutes'

# Application dirs
app_data = BASE_DIR + '/data/'                              # data_train.tsv, data_test.tsv
app_data_remote     = 'deepnc:/mods/data/'
app_data_raw        = BASE_DIR + '/data/raw/'
app_data_features   = BASE_DIR + '/data/features/tsv/'      # (conn, dns, http, sip, ssh, ssl), (hpc)
app_data_train      = BASE_DIR + '/data/train/'             # temporary file
app_data_test       = BASE_DIR + '/data/test/'              # temporary file
app_data_predict    = BASE_DIR + '/data/predict/'
app_data_plot       = BASE_DIR + '/data/plot/'
app_data_results    = BASE_DIR + '/data/results/'
app_models          = BASE_DIR + '/models/'
app_models_remote   = 'deepnc:/mods/models/'
app_checkpoints     = BASE_DIR + '/checkpoints/'
app_visualization   = BASE_DIR + '/visualization/'

# Datapools: window-slide
ws_choices = ['w01h-s10m', 'w10m-s01m', 'w10m-s10m']
ws_choice = ws_choices[0]
# ws_choice = ws_choices[2]         # tumbling windows or HPC

train_ws_choices = test_ws_choices = ws_choices
train_ws = test_ws = ws_choice


# Data selection query
# HPC core query
# data_select_query = 'hpc|sum_value~cores#window_start,window_end'

# DEEP network monitoring queries
data_select_query = 'conn|in_count_uid~A;ssh|in~B#window_start,window_end'

# default query for DEEP = paper plot query (prediction graphs)
# data_select_query = \
#     'conn|in_count_uid~in|out_count_uid~out;' +\
#     'dns|in_distinct_query~in_distinct;' +\
#     'ssh|in' +\
#     '#window_start,window_end'

# paper query with 8 features
# data_select_query = \
#     'conn|in_count_uid~in|out_count_uid~out;' +\
#     'dns|in_count_uid~in|in_distinct_query~in_distinct;' +\
#     'sip|in_count_uid~in;' +\
#     'http|in;' +\
#     'ssh|in;' +\
#     'ssl|in' +\
#     '#window_start,window_end'

# SIP query: sip je na hranici s tym co sa da/neda molelovat. Je to v zavislost od dat pouzitych na train
# data_select_query = \
#     'conn|in_count_uid~in;' +\
#     'sip|in_count_uid~in' +\
#     '#window_start,window_end'

# conn payload examples
#       in_sum_orig_bytes: niekto od nas nieco stahuje z vonka dnu
#       in_sum_resp_bytes: niekto z vonku uploaduje na nase napr. ftp server
#       out_sum_orig_bytes:
#       out_sum_resp_bytes: stahovanie dat z nasej siete smerom von napr. z nasich webovych serverov

# data_select_query = \
#    'conn|in_sum_orig_bytes~in_sum_orig_mb|in_sum_resp_bytes~in_sum_resp_mb' +\
#        '|out_sum_orig_bytes~out_sum_orig_mb|out_sum_resp_bytes~out_sum_resp_mb' +\
#    '#window_start,window_end'

# data_select_query = \
#     'conn|in_count_uid|out_count_uid' +\
#         '|in_sum_orig_bytes~in_sum_orig_mb|in_sum_resp_bytes~in_sum_resp_mb' +\
#         '|out_sum_orig_bytes~out_sum_orig_mb|out_sum_resp_bytes~out_sum_resp_mb' +\
#     '#window_start,window_end'

# data_select_query = \
# 'conn|in_count_uid|out_count_uid' + \
#         '|in_sum_orig_bytes~in_sum_orig_mb|in_sum_resp_bytes~in_sum_resp_mb' + \
#         '|out_sum_orig_bytes~out_sum_orig_mb|out_sum_resp_bytes~out_sum_resp_mb;' + \
#     'dns|in_count_uid|out_count_uid' +\
#         '|in_distinct_query|out_distinct_query' +\
#         '|in_RD_true|out_RD_true;' +\
#     'sip|in_count_uid|out_count_uid;' +\
#     'http|in|out|internal;' +\
#     'ssh|in|out|internal;' +\
#     'ssl|in|out|internal' +\
#     '#window_start,window_end'

train_data_select_query = test_data_select_query = data_select_query


# data filename defaults
data_filename_train = 'data_train.tsv'
data_filename_test  = 'data_test.tsv'


# data range defaults

# DEEP data
# train_time_range_begin = '20200415'       # 2 weeks     # very small data for fast train
# train_time_range_begin = '20200401'       # 1 month
# train_time_range_begin = '20190201'       # 3 months - mods2 - paper plot 3m2d
# train_time_range_begin = '20181101'       # 6 months - k (GTX1070) + p (K20) experiments
# train_time_range_begin = '20180801'       # 9 months
# train_time_range_begin = '20180501'       # 1 year
# train_time_range_end   = '20200430'                         # included

train_time_range_begin = '20200415'
train_time_range_end   = '20200430'

test_time_range_begin = '20200501'
test_time_range_end   = '20200507'

# test_time_range_begin = '20200501'
# test_time_range_end   = '20200502'      # mods2 - paper plot - 2 days
# test_time_range_end   = '20200530'      # 1 month
# test_time_range_end   = '20200630'      # 2 months for test


# HPC data
# train_time_range_begin = '20140315'
# train_time_range_end   = '20160314'
#
# test_time_range_begin = '20160315'
# test_time_range_end   = '20160615'


# Excluded data defaults
train_time_ranges_excluded = data_train_excluded = []       # data that will NOT go to model training
test_time_ranges_excluded  = data_test_excluded = []        # data that will NOT go to model testing


# Training parameters defaults - changeable
multi_headed = False            # defaul = False = model multivariate
model_delta = True              # True --> first order differential = predikuje len zmeny
sequence_len = 12               # p in <6, 18> for w01h-s10m (default=12)
sequence_len_y = 1              # s2s: where sequence_len_y < sequence_len
steps_ahead = 1                 # k in <1, 12> for w01h-s10m; k < p
# model_types = ['MLP', 'Conv1D', 'autoencoderMLP', 'LSTM', 'GRU', 'bidirectLSTM', 'seq2seqLSTM', 'stackedLSTM', 'attentionLSTM', 'TCN', 'stackedTCN']
# model_types = ['MLP', 'Conv1D', 'autoencoderMLP', 'LSTM', 'GRU', 'bidirectLSTM', 'seq2seqLSTM', 'stackedLSTM', 'attentionLSTM', 'TCN']
# model_types = ['MLP', 'Conv1D', 'autoencoderMLP', 'LSTM', 'GRU', 'bidirectLSTM', 'seq2seqLSTM', 'stackedLSTM']
model_types = ['LSTM']
model_type = model_types[0]
repeat_num = 1                  # wrapper defaults=10: model stability = average of n-repeated experiments


# Training defaults - rarely changed
blocks = 6                      # number of RNN blocks (default=12)
num_epochs = 20                 # number of training epochs (default=100)
epochs_patience = 5             # early stopping (default=10)
batch_size = 1                  # faster training --> to be tested later
batch_size_test = 1             # don't change

stacked_blocks = 3              # 1 = no stack
batch_normalization = False     # no significant effect when used with ADAM
dropout_rate = 1.0              # range <0.5, 0.8>, 0.0=no outputs, 1.0=no dropout

# remove_peak = False           # can be removed; we don't use; True --> worse predictions due to time-series nature


# common defaults
model_name_all = list_dir(app_models, '*.zip')
model_name = 'model-deploy'
fill_missing_rows_in_timeseries = True      # fills missing rows in time series data


# Evaluation metrics on real values
eval_metrics = ['SMAPE', 'R2', 'COSINE']    # 'MAPE', 'RMSE'
eval_filename = 'eval.tsv'

# Plotting
plot = True
plot_train = False
plot_model = False
plot_image_filename = "plot_image.png"
fig_size_x = 10                                 # max 2^16 pixels = 650 inch
fig_size_y = 2
colors = ["#017b92", "#f97306", "#2baf6a"]      # ["jade green", "orange", "ocean"]  https://xkcd.com/color/rgb/


# pandas defaults
pd_sep = '\t'                               # ',' for csv
pd_skiprows = 0
pd_skipfooter = 0
pd_engine = 'python'
pd_header = 0

# Auxiliary: DayTime format
format_string = '%Y-%m-%d %H:%M:%S'
format_string_parquet = '%Y-%m-%d %H_%M_%S'     # parquet format without ":"
timezone = 3600


##### @stevo #####

def set_common_args():
    common_args = {
        'bootstrap_data': {
            'default': True,
            'choices': [True, False],
            'help': 'Download data from remote datastore',
            'required': False
        }
    }
    return common_args


def set_pandas_args():
    pandas_args = {
        # 'pd_sep': {
        #     'default': pd_sep,
        #     'help': '',
        #     'required': False
        # },
        'pd_skiprows': {
            'default': pd_skiprows,
            'help': '',
            'required': False
        },
        'pd_skipfooter': {
            'default': pd_skipfooter,
            'help': '',
            'required': False
        },
        # 'pd_engine': {
        #     'default': pd_engine,
        #     'help': '',
        #     'required': False
        # },
        'pd_header': {
            'default': pd_header,
            'help': '',
            'required': False
        }
    }
    return pandas_args


def set_train_args():
    train_args = {
        'model_name': {
            'default': model_name,
            'help': 'Name of the model to train',
            'type': str,
            'required': False
        },
        'data': {
            'default': data_train,
            'choices': data_train_all,
            'help': 'Training data to train on',
            'required': False
        },
        'multivariate': {
            'default': multivariate,
            'help': '',
            'required': False
        },
        'sequence_len': {
            'default': sequence_len,
            'help': '',
            'required': False
        },
        'model_delta': {
            'default': model_delta,
            'choices': [True, False],
            'help': '',
            'required': False
        },
        'interpolate': {
            'default': interpolate,
            'choices': [True, False],
            'help': '',
            'required': False
        },
        'model_type': {
            'default': model_type,
            'choices': model_types,
            'help': '',
            'required': False
        },
        'num_epochs': {
            'default': num_epochs,
            'help': 'Number of epochs to train on',
            'required': False
        },
        'epochs_patience': {
            'default': epochs_patience,
            'help': '',
            'required': False
        },
        'blocks': {
            'default': blocks,
            'help': '',
            'required': False
        },
        'steps_ahead': {
            'default': steps_ahead,
            'help': 'Number of steps to predict ahead of current time',
            'required': False
        }
    }
    train_args.update(set_pandas_args())
    train_args.update(set_common_args())
    return train_args


def set_predict_args():
    predict_args = {
        'model_name': {
            'default': model_name,
            'choices': model_name_all,
            'help': 'Name of the model used for prediction',
            'type': str,
            'required': False
        },
        'batch_size': {
            'default': batch_size_test,
            'help': '',
            'required': False
        }
    }
    predict_args.update(set_pandas_args())
    predict_args.update(set_common_args())
    return predict_args


def set_test_args():
    test_args = {
        'model_name': {
            'default': model_name,
            'help': 'Name of the model used for a test',
            'type': str,
            'required': False
        },
        'data': {
            'default': test_data,
            'help': 'Data to test on',
            'required': False
        },
        'batch_size': {
            'default': batch_size_test,
            'help': '',
            'required': False
        }
    }
    test_args.update(set_pandas_args())
    test_args.update(set_common_args())
    return test_args
