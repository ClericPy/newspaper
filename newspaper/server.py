from .views import app
import uvicorn


def main():
    uvicorn.run(
        app,
        host='127.0.0.1',
        port=9001,
        proxy_headers=True,
    )
    # logger=app.logger)
