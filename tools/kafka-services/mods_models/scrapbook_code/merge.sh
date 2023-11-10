#!/bin/bash
head -n 1 buffer-all-1M-2021-05-26.tsv > buffer.tsv && tail -n+2 -q buffer-all-1M-2021-*.tsv | sort -u -t$'\t' -k1,1 >> buffer.tsv 
