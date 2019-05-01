from newspaper.crawler.main import outlands_request
import asyncio


async def test():
    ss = await outlands_request({
        'method': 'get',
        'url': 'https://pyfound.blogspot.com/'
    }, 'u8')
    print(ss)
    return ss


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
