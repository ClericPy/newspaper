#!/bin/bash

ps aux|grep 'newspaper-'|grep 'run_server.py'|awk '{print $2}'|xargs kill
echo "server stoped"
echo

DIR=$(cd `dirname $0`/..; pwd)
cd $DIR
nohup pipenv run python run_server.py & >/dev/null
echo "server started"
echo
