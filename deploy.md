
## 首次部署
0. install python 3.7+
1. git clone ...
2. pipenv install
3. python3.7 update_systemd_config.py
4. 新建 JSON 格式配置文件 /var/newspaper.conf
   1. {"anti_gfw": {"url": "这里填写翻墙服务的地址, 如果没有则使用 http://localhost"}, "mysql_config": {"mysql_host": "", "mysql_port": 3306, "mysql_user": "", "mysql_password": "", "mysql_db": "db"}}
   2. 当然环境变量 export newspaper_config 上面的 JSON 也是可以的
5. systemctl --user enable newspaper_web.service; systemctl --user start newspaper_web.service
6. systemctl --user enable newspaper_spider.timer; systemctl --user start newspaper_spider.timer
7. 绑定域名, 并配置 nginx 托管相关端口, 支持 SSL




### vscode task 升级更新脚本
```git co master ; git merge dev; git push; git co dev;ssh aliyun 'cd newspaper/bin;sh git-sync.sh;python3.7 update_systemd_config.py;systemctl daemon-reload;systemctl --user restart newspaper_web.service'```
