import cv2
import threading
import time
import subprocess
import os


class VideoRecorder():
    # Video class based on openCV
    def __init__(self):

        self.open = False
        self.device_index = 1
        # fps should be the minimum constant rate at which the camera can capture images (with no decrease in speed over time; testing is required)
        self.fps = 20
        self.fourcc = "MJPG"
        self.frameSize = (704, 480)
        self.video_filename = ""
        self.video_cap = cv2.VideoCapture(self.device_index)
        self.start_time = None
        self.end_time = None

    # Save a single frame to the file
    def save_frame(self):
        ret, video_frame = self.video_cap.read()
        if ret:
            cv2.imwrite("frame.jpg", video_frame)

    # Video starts being recorded
    def record(self):
        self.open = True
        self.video_writer = cv2.VideoWriter_fourcc(*self.fourcc)
        self.video_filename = "temp_" + \
            time.strftime("%Y-%m-%d_%H-%M-%S") + ".avi"
        self.video_out = cv2.VideoWriter(
            self.video_filename, self.video_writer, self.fps, self.frameSize)
        self.start_time = time.time()
        self.frame_counts = 1

        while self.open:
            ret, video_frame = self.video_cap.read()
            if ret:

                self.video_out.write(video_frame)
                self.frame_counts += 1
                if self.frame_counts % 5 == 0:
                    cv2.imwrite("frame.jpg", video_frame)
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
    cmd = "/Users/jonah/Documents/ScoutVideo/ffmpeg -r " + str(recorded_fps) + \
        " -i " + input + " -r " + \
        str(fps) + " -vcodec libx264 -crf 24 " + output
    subprocess.call(cmd, shell=True, stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL)
    os.remove(input)


if __name__ == "__main__":
    recorder = VideoRecorder()
    recorder.start()
    # input("Press enter to stop recording")
    time.sleep(30)
    recorder.stop()
    print("Recorded fps:", recorder.frame_counts /
          (recorder.end_time - recorder.start_time))

    print("Encoding video")
    encode_output(recorder.frame_counts, recorder.start_time,
                  recorder.end_time, recorder.fps, recorder.video_filename, "test.mp4")
    print("Done")
