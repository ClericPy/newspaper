#! python3

from .server import api
from .views import *


def main():
    api.run(address="localhost", port=8111, access_log=0)


if __name__ == "__main__":
    main()
