import subprocess
import signal
import shlex
import time
from enum import Enum


class RecorderMode(Enum):
    RECORD = 0,
    IDLE = 1


class GstreamerRecorder():
    def __init__(self):
        self.filename = ""
        self.active = False
        self.device = "/dev/video1"
        self.width = 1920
        self.height = 1080
        self.idle_command = "gst-launch-1.0 -e v4l2src device=" + self.device + " ! 'video/x-raw,width=" + str(self.width) + ",height=" + str(
            self.height) + "' ! videorate ! 'video/x-raw,framerate=4/1' ! videoconvert ! jpegenc ! multifilesink location=frame.jpg"
        self.record_command = "gst-launch-1.0 -e v4l2src device=" + self.device + " ! 'video/x-raw,width=" + str(self.width) + ",height=" + str(
            self.height) + "' ! tee name=t ! queue ! videoconvert ! omxh264enc bitrate=3000000 ! h264parse ! mp4mux ! filesink location=$FILENAME t. ! queue ! videorate ! 'video/x-raw,framerate=4/1' ! videoconvert ! jpegenc ! multifilesink location=frame.jpg"

    def start(self, mode, filename=None):
        if self.active:
            self.stop()
        self.active = True
        self.filename = filename
        if mode == RecorderMode.RECORD:
            command = self.record_command.replace("$FILENAME", filename)
        else:
            command = self.idle_command
        self.process = subprocess.Popen(shlex.split(
            command), stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

    def stop(self):
        if self.active:
            self.process.send_signal(signal.SIGINT)
            self.process.wait()
            self.active = False


streamer = GstreamerRecorder()
streamer.start(RecorderMode.IDLE)
print("Started")
time.sleep(10)
print("Stopping")
streamer.stop()
