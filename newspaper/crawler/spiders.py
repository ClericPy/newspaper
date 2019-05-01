import asyncio
import json
import typing
import zlib
from functools import wraps

from torequests.dummy import Requests
from torequests.utils import ttime

from ..config import global_configs

online_spiders = []

req = Requests()


async def outlands_request(request_dict: dict, encoding: str = 'u8') -> str:
    """小水管不开源, 无法用来 FQ.

    例:
        async def test():
            ss = await outlands_request({
                'method': 'get',
                'url': 'https://pyfound.blogspot.com/'
            }, 'u8')
            print(ss)
            return ss
    """
    data = json.dumps(request_dict)
    data = zlib.compress(data.encode('u8'))
    url = global_configs['anti_gfw']['url']
    r = await req.post(url, timeout=60, data=data)
    if r:
        return zlib.decompress(r.content).decode(encoding)
    else:
        return r.text


def register_online(function: typing.Callable) -> typing.Callable:
    """把爬虫注册到线上可用列表

    :param function: 爬虫函数, 一般没有参数.
    :type function: typing.Callable
    :return: 爬虫函数, 一般没有参数.
    :rtype: typing.Callable
    """

    online_spiders.append(function)
    return function


@register_online
async def python_news() -> list:
    """Python Latest News. 
    全部历史文章:
    https://pyfound.blogspot.com/search?updated-max=2007-01-04T10:00:00-05:00&max-results=9999"""
    await asyncio.sleep(1)
    return ['text']


if __name__ == "__main__":
    print(f'online online_spiders: {len(online_spiders)}')
