import logging
from threading import Thread

import common_cli_args  as cli
from common_cli_args import setup_cli_args
from common_constants import LOGGING_ARGS
from flask import Flask
from location_client import LocationClient

http = Flask(__name__)


@http.route("/count")
def val_count():
    global count
    return "Read {0} values".format(count)


def read_values():
    global count
    while True:
        print("Got location: {0}".format(locations.get_xy()))
        count += 1


if __name__ == "__main__":
    # Parse CLI args
    args = setup_cli_args(cli.grpc)

    # Setup logging
    logging.basicConfig(**LOGGING_ARGS)

    # Start client
    locations = LocationClient(args["grpc"]).start()

    # Run read_values in a thread
    count = 0
    Thread(target=read_values).start()

    http.run()
