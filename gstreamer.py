import subprocess
import signal
import shlex
import time
from enum import Enum
import os


class RecorderMode(Enum):
    RECORD = 0,
    IDLE = 1


def run_command(args, output=True):
    if output:
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        result = stdout.decode("utf-8")
        result += stderr.decode("utf-8")
        return result
    else:
        process = subprocess.call(
            args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return


def find_device(target):
    devices = run_command(["v4l2-ctl", "--list-devices"]).split("\n")
    try:
        line = [x.split("(")[0][:-1] for x in devices].index(target) + 1
    except:
        return "/dev/video0"
    else:
        return devices[line][1:]


class GstreamerRecorder():
    filename = ""

    def __init__(self):
        self.active = False
        self.device_name = "Logitech Webcam C930e"
        self.width = 1920
        self.height = 1080

    def __construct_command(self):

        self.device = find_device(self.device_name)
        self.idle_command = "gst-launch-1.0 -e v4l2src device=" + self.device + " ! 'video/x-raw,width=" + str(self.width) + ",height=" + str(
            self.height) + "' ! videorate ! 'video/x-raw,framerate=10/1' ! videoconvert ! jpegenc ! multifilesink location=frame.jpg"
        # self.record_command = "gst-launch-1.0 -e v4l2src device=" + self.device + " ! 'video/x-raw,width=" + str(self.width) + ",height=" + str(
        #     self.height) + ",framerate=30/1' ! tee name=t ! queue ! videoconvert ! nvh264enc ! h264parse ! mp4mux ! filesink location=$FILENAME t. ! queue ! videorate ! 'video/x-raw,framerate=4/1' ! videoconvert ! jpegenc ! multifilesink location=frame.jpg"

        # self.record_command = "gst-launch-1.0 -e v4l2src device=" + self.device + " ! 'image/jpeg,width=" + str(self.width) + ",height=" + str(
        #     self.height) + ",framerate=30/1' ! jpegdec ! videoconvert ! nvh264enc ! h264parse ! mp4mux ! filesink location=$FILENAME "

        self.record_command = "gst-launch-1.0 -e v4l2src device=" + self.device + " ! 'image/jpeg,width=" + str(self.width) + ",height=" + str(
            self.height) + ",framerate=30/1' ! tee name=t ! queue ! jpegdec ! videoconvert ! nvh264enc ! h264parse ! mp4mux ! filesink location=$FILENAME t. ! queue ! videorate ! 'image/jpeg,framerate=4/1' ! multifilesink location=frame.jpg"



    def start(self, mode, filename=None):
        if self.active:
            self.stop()
        self.active = True
        self.filename = filename
        self.__construct_command()
        if mode == RecorderMode.RECORD:
            print("Filename " + filename)
            command = self.record_command.replace("$FILENAME", filename)
        else:
            command = self.idle_command
        os.system("killall gst-launch-1.0")
        self.process = subprocess.Popen(shlex.split(
            command), stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

    def stop(self):
        if self.active:
            self.process.send_signal(signal.SIGINT)
            self.process.wait()
            self.active = False
