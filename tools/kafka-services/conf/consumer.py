import datetime

kafka = {
    'bootstrap_servers': {
        'in': ['147.213.65.206:9093', '147.213.65.206:9094', '147.213.65.206:9095'],
        'out': ['147.213.65.206:9093', '147.213.65.206:9094', '147.213.65.206:9095']
    },
    'topics': {
        'in': 'mods',
        'out': 'mods-agg-10m'
    }
}

elasticsearch = {
    'host': '127.0.0.1:9200',
    'index': 'mods-10m'
}

net_direction = {
    'regex': r'147\.213\..+',  # regex matching local networks. set to empty, if not used
    'field_name': 'mods_dir',  # name of the field containing networking direction according to local_networks_re
    'orig_field': 'id.orig_h',
    'resp_field': 'id.resp_h'
}

#
# time window length as well as minimum time to wait for delayed logs
#
aggregation_period = datetime.timedelta(
    minutes=10
)

#
# specify rules on data cleaning
#
data_cleaning_rules = {
    'conn': {
        'to_numeric': {
            'coerce': [
                'duration',
                'orig_bytes',
                'resp_bytes'
            ]
        },
        'fillna': {
            0: [
                'duration',
                'orig_bytes',
                'resp_bytes'
            ]
        },
        'astype': {
            float: [
                'duration'
            ],
            int: [
                'orig_bytes',
                'resp_bytes'
            ]
        }
    }
}

#
# specify how to aggregate rows of particular columns in sliding window
#
# protocol -> column -> [agg. functions]
#
aggregation_rules = {
    'agg': {
        'conn': {
            'uid': ['count', 'nunique'],
            'orig_bytes': ['sum'],
            'resp_bytes': ['sum'],
            'duration': ['mean']
        },
        'dns': {
            'uid': ['count', 'nunique'],
            'query': ['count', 'nunique'],
            'proto': ['count', 'nunique']
        },
        'sip': {
            'uid': ['count', 'nunique'],
            'id.orig_h': ['count', 'nunique'],
            'id.orig_p': ['count', 'nunique'],
            'id.resp_h': ['count', 'nunique'],
            'id.resp_p': ['count', 'nunique']
        },
        'ssh': {
            'uid': ['count', 'nunique']
        },
        'ssl': {
            'uid': ['count', 'nunique']
        },
        'http': {
            'uid': ['count', 'nunique']
        }
    },
    'groupby': {
        'dns': {
            'AA': ['count'],
            'RA': ['count'],
            'RD': ['count'],
            'TC': ['count'],
            'rejected': ['count']
        }
    }
}

#
# fields being collected before aggregation
#
# protocol -> [columns]
#
# !!! do not edit. this variable is populated automatically !!!
distillation_rules = {}

# extract column names
for k, v in aggregation_rules.items():
    for p, r in v.items():
        if p not in distillation_rules:
            distillation_rules[p] = []
        distillation_rules[p].extend(r)

# get sorted unique column names
for k in distillation_rules:
    # add fields required for networking direction resolution
    if net_direction['regex']:
        distillation_rules[k].extend([net_direction['orig_field'], net_direction['resp_field']])
    distillation_rules[k] = sorted(set(distillation_rules[k]))
