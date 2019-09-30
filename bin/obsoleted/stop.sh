#!/bin/bash
ps aux|grep 'newspaper-'|grep 'run_server.py'|awk '{print $2}'|xargs kill
echo "server stoped"
echo
