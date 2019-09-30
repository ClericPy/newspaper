import pathlib
user_systemd_dir = pathlib.Path.home() / '.config/systemd'
if not user_systemd_dir.is_dir():
    user_systemd_dir.mkdir()

this_fp = pathlib.Path(__file__)

# web 服务启动

newspaper_web_service = r'''
[Unit]
Description=newspaper web service

[Service]
Type=simple
ExecStart=cd {str(this_fp.parent.parent)};/usr/local/bin/pipenv run python run_server.py

'''
newspaper_web_service_fp = user_systemd_dir / 'newspaper_web.service'
newspaper_web_service_fp.write_text(newspaper_web_service, encoding='utf-8')

# 爬虫服务

newspaper_spider_service = fr'''
[Unit]
Description=newspaper spider service

[Service]
Type=simple
ExecStart=cd {str(this_fp.parent.parent)};/usr/local/bin/pipenv run python crawl_online.py

'''
newspaper_spider_service_fp = user_systemd_dir / 'newspaper_spider.service'
newspaper_spider_service_fp.write_text(newspaper_spider_service,
                                       encoding='utf-8')

# 爬虫定时器

newspaper_spider_timer = r'''
[Unit]
Description=newspaper spider timer

[Timer]
OnBootSec=10min
OnUnitActiveSec=15min
Unit=newspaper_spider.service

[Install]
WantedBy=multi-user.target
WantedBy=network-online.target
'''
newspaper_spider_timer_fp = user_systemd_dir / 'newspaper_spider.timer'
newspaper_spider_timer_fp.write_text(newspaper_spider_service, encoding='utf-8')
