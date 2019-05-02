"""
启动后端 API 服务
"""
from newspaper.server import api
import asyncio


def main():
    api.run(address="localhost", port=8111, access_log=0)


if __name__ == "__main__":
    main()
