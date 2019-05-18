#!/bin/bash
DIR=$(cd `dirname $0`; pwd)
cd $DIR
sh stop.sh
sh start.sh > /dev/null
