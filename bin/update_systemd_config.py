import pathlib
user_systemd_dir = pathlib.Path.home() / '.config/systemd/user'
if not user_systemd_dir.is_dir():
    user_systemd_dir.mkdir()

newspaper_product_dir = pathlib.Path(
    __file__).absolute().parent.parent.absolute()

# web 服务启动

newspaper_web_service = fr'''
[Unit]
Description=newspaper web service

[Service]
Type=simple
ExecStart=/usr/local/bin/pipenv run python run_server.py
WorkingDirectory={newspaper_product_dir}
[Install]
WantedBy=multi-user.target
WantedBy=network-online.target
'''
newspaper_web_service_fp = user_systemd_dir / 'newspaper_web.service'
newspaper_web_service_fp.write_text(newspaper_web_service, encoding='utf-8')

# 爬虫服务

newspaper_spider_service = fr'''
[Unit]
Description=newspaper spider service

[Service]
Type=simple
ExecStart=/usr/local/bin/pipenv run python crawl_online.py
WorkingDirectory={newspaper_product_dir}

[Install]
WantedBy=multi-user.target
WantedBy=network-online.target
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
newspaper_spider_timer_fp.write_text(newspaper_spider_timer, encoding='utf-8')
