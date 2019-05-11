#!/bin/bash
# 从最新的 master 分支拉代码, 使用 deploy key
# ensure dir
DIR=$(cd `dirname $0`/../config; pwd)

cd $DIR&&eval `ssh-agent -s`&&ssh-add "/root/.ssh/id_rsa_fleeting"&&git fetch&&git reset --hard master&&git pull&&git reset --hard master&&python3.6 set_supervisord_config.py&&python3.6 set_crontab_tasks.py&&supervisorctl update&&git log -p -1
# cd $DIR&&eval `ssh-agent -s`&&ssh-add "/root/.ssh/id_rsa_fleeting"&&git fetch&&git reset --hard master&&git pull&&git reset --hard master&&pipenv install --skip-lock&&python3.6 set_supervisord_config.py&&python3.6 set_crontab_tasks.py&&supervisorctl update&&git log -p -1
# cd $DIR&&eval `ssh-agent -s`&&ssh-add "/root/.ssh/id_rsa_fleeting"&&git reset --hard master&&git pull&&git reset --hard master&&pipenv install --skip-lock&&python3.6 set_supervisord_config.py&&python3.6 set_crontab_tasks.py&&supervisorctl update
