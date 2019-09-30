#!/bin/bash
DIR=$(cd `dirname $0`/..; pwd)
cd $DIR
nohup pipenv run python run_server.py &
echo "server started"
echo
