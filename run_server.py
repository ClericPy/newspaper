"""
启动后端 API 服务
"""
import uvicorn

from newspaper.server import app


def main():
    uvicorn.run(app,
                host='127.0.0.1',
                port=9001,
                proxy_headers=True,
                logger=app.logger)


if __name__ == "__main__":
    main()
