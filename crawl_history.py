from newspaper.crawler.main import history_workflow
import asyncio
"""
采集历史文章脚本
1. 本地脚本
2. 执行历史文章抓取任务, 并将文章入库
3. 将需要抓历史文章的内容源的函数加装饰器 register_history, 就会被自动调用
4. 一般抓历史文章的任务只在第一次收录时候使用, 后期使用 online_spiders 保持更新
"""

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(history_workflow())
