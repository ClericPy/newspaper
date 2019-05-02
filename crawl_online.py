from newspaper.crawler.main import online_workflow
import asyncio
"""
采集线上爬虫脚本
1. 本地脚本 / 线上脚本 皆可. crontab 任务
2. 执行执行常规抓取任务, 并将文章入库
3. 将需要抓历史文章的内容源的函数加装饰器 register_history, 就会被自动调用
"""

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(online_workflow())
