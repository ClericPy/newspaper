"""
启动后端 API 服务
"""
from newspaper.server import api


def main():
    api.run(address="127.0.0.1", port=9001, access_log=1, logger=api.logger)


if __name__ == "__main__":
    main()
