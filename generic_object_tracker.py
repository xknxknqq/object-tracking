import logging
import sys
import traceback
from threading import Lock

import camera
import common_cli_args  as cli
import cv2
import opencv_utils as utils
from common_cli_args import setup_cli_args
from common_utils import currentTimeMillis, is_raspi
from contour_finder import ContourFinder
from http_server import HttpServer
from location_server import LocationServer

# I tried to include this in the constructor and make it depedent on self.__leds, but it does not work
if is_raspi():
    from blinkt import set_pixel, show


class GenericObjectTracker(object):
    def __init__(self,
                 bgr_color,
                 width,
                 percent,
                 minimum,
                 hsv_range,
                 grpc_port=50051,
                 display=False,
                 flip_x=False,
                 flip_y=False,
                 usb_camera=False,
                 leds=False,
                 camera_name="",
                 http_host="localhost:8080",
                 http_delay_secs=0.5):
        self.__width = width
        self.__percent = percent
        self.__orig_width = width
        self.__orig_percent = percent
        self.__minimum = minimum
        self.__display = display
        self.__flip_x = flip_x
        self.__flip_y = flip_y
        self.__leds = leds
        self.__stopped = False
        self.__http_launched = False
        self.__http_host = http_host
        self.__cnt = 0
        self.__last_write_millis = 0
        self.__current_image_lock = Lock()
        self.__current_image = None
        self._prev_x, self._prev_y = -1, -1
        self.__contour_finder = ContourFinder(bgr_color, hsv_range)
        self.__location_server = LocationServer(grpc_port)
        self.__cam = camera.Camera(use_picamera=not usb_camera)
        self.__http_server = HttpServer(camera_name, self.__http_host, http_delay_secs, self.get_image)

    @property
    def width(self):
        return self.__width

    @width.setter
    def width(self, width):
        if 200 <= width <= 4000:
            self.__width = width
            self._prev_x, self._prev_y = -1, -1

    @property
    def percent(self):
        return self.__percent

    @percent.setter
    def percent(self, percent):
        if 2 <= percent <= 98:
            self.__percent = percent
            self._prev_x, self._prev_y = -1, -1

    @property
    def minimum(self):
        return self.__minimum

    @property
    def display(self):
        return self.__display

    @property
    def flip_x(self):
        return self.__flip_x

    @property
    def flip_y(self):
        return self.__flip_y

    @property
    def stopped(self):
        return self.__stopped

    @property
    def contour_finder(self):
        return self.__contour_finder

    @property
    def location_server(self):
        return self.__location_server

    @property
    def cam(self):
        return self.__cam

    @property
    def http_server(self):
        return self.__http_server

    @property
    def cnt(self):
        return self.__cnt

    @cnt.setter
    def cnt(self, val):
        self.__cnt = val

    @property
    def last_write_millis(self):
        return self.__last_write_millis

    @last_write_millis.setter
    def last_write_millis(self, val):
        self.__last_write_millis = val

    def stop(self):
        self.__stopped = True
        self.__location_server.stop()

    def clear_leds(self):
        self.set_left_leds([0, 0, 0])
        self.set_right_leds([0, 0, 0])

    def set_left_leds(self, color):
        if self.__leds:
            for i in range(0, 4):
                set_pixel(i, color[2], color[1], color[0], brightness=0.05)
            show()

    def set_right_leds(self, color):
        if self.__leds:
            for i in range(4, 8):
                set_pixel(i, color[2], color[1], color[0], brightness=0.05)
            show()

    def display_image(self, image):
        if self.display:
            cv2.imshow("Image", image)

            key = cv2.waitKey(1) & 0xFF

            if key == 255:
                pass
            elif key == ord("w"):
                self.width -= 10
            elif key == ord("W"):
                self.width += 10
            elif key == ord("-") or key == ord("_") or key == 0:
                self.percent -= 1
            elif key == ord("+") or key == ord("=") or key == 1:
                self.percent += 1
            elif key == ord("r"):
                self.width = self.__orig_width
                self.percent = self.__orig_percent
            elif key == ord("s"):
                utils.write_image(image, log_info=True)
            elif key == ord("q"):
                self.stop()

    def get_image(self):
        with self.__current_image_lock:
            if self.__current_image is None:
                return []
            retval, buf = utils.encode_image(self.__current_image)
            return buf.tobytes()

    def serve_image(self, image):
        if self.http_server.is_enabled():
            now = currentTimeMillis()
            if now - self.last_write_millis > 100:
                with self.__current_image_lock:
                    self.__current_image = image
                self.last_write_millis = now

    def start(self):
        try:
            self.location_server.start()
        except BaseException as e:
            logging.error("Unable to start location server [{0}]".format(e))
            traceback.print_exc()
            sys.exit(1)

        self.location_server.write_location(-1, -1, 0, 0, 0)

    def markup_image(self):
        return self.display or self.http_server.is_enabled()

    @staticmethod
    def cli_args():
        return setup_cli_args(cli.bgr,
                              cli.usb,
                              cli.width,
                              cli.percent,
                              cli.min,
                              cli.range,
                              cli.grpc_port,
                              cli.leds,
                              cli.flip_x,
                              cli.flip_y,
                              cli.camera_optional,
                              cli.http_host,
                              cli.http_delay,
                              cli.display,
                              cli.verbose)
