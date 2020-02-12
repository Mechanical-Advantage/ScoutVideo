import cv2
import threading
import time
import subprocess
import os


class VideoRecorder():
    # Video class based on openCV
    def __init__(self, start_thread=False):
        self.open = False
        self.device_index = 1
        # fps should be the minimum constant rate at which the camera can capture images (with no decrease in speed over time; testing is required)
        self.fps = 30
        self.fourcc = "XVID"
        self.frameSize = (1920, 1080)
        self.video_filename = ""
        self.video_cap = cv2.VideoCapture(self.device_index)
        # self.video_cap.set(6, self.fourcc)
        self.video_cap.set(3, self.frameSize[0])
        self.video_cap.set(4, self.frameSize[1])
        self.start_time = None
        self.end_time = None
        if start_thread:
            self.save_thread = threading.Thread(
                target=self.__save_thread, daemon=True)
            self.save_thread.start()

    # Save a single frame to the file
    def save_frame(self):
        try:
            ret, video_frame = self.video_cap.read()
            if ret:
                cv2.imwrite("frame.jpg", video_frame)
        except:
            pass

    # Regularly save a frame
    def __save_thread(self):
        while True:
            time.sleep(0.25)
            self.save_frame()

    # Video starts being recorded
    def record(self):
        self.open = True
        self.video_writer = cv2.VideoWriter_fourcc(*self.fourcc)
        self.video_filename = "temp_" + \
            time.strftime("%Y-%m-%d_%H-%M-%S") + ".mp4"
        self.video_out = cv2.VideoWriter(
            self.video_filename, self.video_writer, self.fps, self.frameSize)
        self.start_time = time.time()
        self.frame_counts = 1

        while self.open:
            ret, video_frame = self.video_cap.read()
            if ret:

                self.video_out.write(video_frame)
                self.frame_counts += 1
                cv2.waitKey(1)
            else:
                break

    # Finishes the video recording therefore the thread too
    def stop(self):
        if self.open:
            self.open = False
            self.end_time = time.time()
            time.sleep(0.5)
            self.video_out.release()
            cv2.destroyAllWindows()

    # Launches the video recording function using a thread
    def start(self):
        video_thread = threading.Thread(target=self.record)
        video_thread.start()


# Re-encode output to H.264 and fix framerate
def encode_output(frame_count, start_time, stop_time, fps, input, output):
    elapsed_time = stop_time - start_time
    recorded_fps = frame_count / elapsed_time
    print(recorded_fps)
    cmd = "ffmpeg -r " + str(recorded_fps) + \
        " -i " + input + " -r " + \
        str(fps) + " -vcodec libx264 -crf 18 " + output
    subprocess.call(cmd, shell=True, stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL)
    # os.remove(input)


if __name__ == "__main__":
    recorder = VideoRecorder()
    recorder.start()
    input("Press enter to stop recording")
    # time.sleep(30)
    recorder.stop()
    print("Recorded fps:", recorder.frame_counts /
          (recorder.end_time - recorder.start_time))

    print("Encoding video")
    encode_output(recorder.frame_counts, recorder.start_time,
                  recorder.end_time, recorder.fps, recorder.video_filename, "test.mp4")
    print("Done")
