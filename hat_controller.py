#!/usr/bin/env python2

import logging
from threading import Thread

import calibrate_servo
import cli_args  as cli
import pantilthat as pth
from cli_args import LOG_LEVEL, GRPC_HOST
from cli_args import setup_cli_args
from hat_servo import HatServo
from location_client import LocationClient
from utils import setup_logging

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Setuo CLI args
    args = setup_cli_args(cli.grpc_host, cli.alternate, cli.calib, cli.verbose)

    alternate = args["alternate"]
    calib = args["calib"]

    setup_logging(level=args[LOG_LEVEL])

    with LocationClient(args[GRPC_HOST]) as client:

        # Create servos
        servo_x = HatServo("Pan", pth.pan, alternate, 1.0, 8)
        servo_y = HatServo("Tilt", pth.tilt, alternate, 1.0, 8)

        if calib:
            calib_t = Thread(target=calibrate_servo.calibrate, args=(client, servo_x, servo_y))
            calib_t.start()
            calib_t.join()
        else:
            if alternate:
                # Set servo X to go first if alternating
                servo_x.ready_event.set()

            try:
                servo_x.start(False, lambda: client.get_x(), servo_y.ready_event if not calib else None)
                servo_y.start(False, lambda: client.get_y(), servo_x.ready_event if not calib else None)
                servo_x.join()
                servo_y.join()
            except KeyboardInterrupt:
                pass
            finally:
                servo_x.stop()
                servo_y.stop()

    logger.info("Exiting...")
