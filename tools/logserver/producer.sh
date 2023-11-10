#!/usr/bin/env bash

bootstrap_servers=${1:-147.213.65.206:9093 147.213.65.206:9094 147.213.65.206:9095}

logs_dir="/storage/bro/logs/current"
protocols=('conn' 'dns' 'http' 'sip' 'ssh' 'ssl')

function producer {
	local key=$1
	local header=$(sed '7q;d' "$logs_dir/$key.log" | sed -E 's/#fields\t//g' | sed -E 's/\t/ /g')
	tail -F ~/logs/current/$key.log | \
	 ./producer.py \
	 --bootstrap-servers $bootstrap_servers \
	 --header $header \
	 --channel 'mods' \
	 --key $key
}

for protocol in "${protocols[@]}"
do
	producer $protocol &
done

trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT
wait
