def test():
    from newspaper.crawler.main import test_spider_workflow
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_spider_workflow())


if __name__ == "__main__":
    test()
