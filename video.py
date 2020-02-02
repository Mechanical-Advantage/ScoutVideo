import cv2
import threading
import time
import subprocess
import os


class VideoRecorder():
    # Video class based on openCV
    def __init__(self):

        self.open = True
        self.device_index = 0
        # fps should be the minimum constant rate at which the camera can capture images (with no decrease in speed over time; testing is required)
        self.fps = 20
        self.fourcc = "MJPG"
        self.frameSize = (640, 480)
        self.video_filename = "temp_" + \
            time.strftime("%Y-%m-%d_%H-%M-%S") + ".avi"
        self.video_cap = cv2.VideoCapture(self.device_index)
        self.video_writer = cv2.VideoWriter_fourcc(*self.fourcc)
        self.video_out = cv2.VideoWriter(
            self.video_filename, self.video_writer, self.fps, self.frameSize)
        self.frame_counts = 1
        self.start_time = time.time()

    # Video starts being recorded
    def record(self):

        timer_start = time.time()
        timer_current = 0

        while(self.open == True):
            ret, video_frame = self.video_cap.read()
            if (ret == True):

                self.video_out.write(video_frame)
                self.frame_counts += 1
                # time.sleep(1 / self.fps)
                # cv2.imshow("Video Frame", video_frame)
                if self.frame_counts % 5 == 0:
                    cv2.imwrite("frame.jpg", video_frame)
                cv2.waitKey(1)
            else:
                break

    # Finishes the video recording therefore the thread too
    def stop(self):

        if self.open == True:
            self.open = False
            self.video_out.release()
            self.video_cap.release()
            cv2.destroyAllWindows()

        else:
            pass

    # Launches the video recording function using a thread
    def start(self):
        video_thread = threading.Thread(target=self.record)
        video_thread.start()


# Re-encode output to H.264 and fix framerate
def encode_output(frame_count, start_time, stop_time, fps, input, output):
    elapsed_time = stop_time - start_time
    recorded_fps = frame_count / elapsed_time
    cmd = "ffmpeg -r " + str(fps) + \
        " -i " + input + " -r " + \
        str(fps) + " -vcodec libx264 -crf 24 " + output
    subprocess.call(cmd, shell=False, stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL)
    os.remove(input)


if __name__ == "__main__":
    recorder = VideoRecorder()
    recorder.start()
    input("Press enter to stop recording")
    recorder.stop()

    print("Encoding video")
    encode_output(recorder, "test.mp4")
    print("Done")
