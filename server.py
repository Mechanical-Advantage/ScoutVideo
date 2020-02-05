import cherrypy
import video
import os
import threading
from multiprocessing import Process
import time

recorder = video.VideoRecorder()


class main_server(object):
    @cherrypy.expose
    def index():
        return """
<html>

<head>
    <title>
        Video Viewer
    </title>
    <script>
        function refresh() {
            document.getElementById('image').src = "frame.jpg?random=" + new Date().getTime()
        }
        setInterval(refresh, 200)

        function send(url) {
            const http = new XMLHttpRequest()
            http.open("POST", url)
            http.send()
        }
    </script>
</head>
<button onclick="send(&quot;start&quot;)">
    Start Recording
</button>
<button onclick="send(&quot;stop&quot;)">
    Stop Recording
</button>
<button onclick="send(&quot;save_frame&quot;)">
    Save Frame
</button>
<br>
<img src="frame.jpg" id="image">

</html>
        """

    @cherrypy.expose
    def save_frame():
        recorder.save_frame()

    @cherrypy.expose
    def start():
        if recorder.open:
            recorder.stop()
        recorder.start()

    @cherrypy.expose
    def stop():
        if recorder.open:
            recorder.stop()
            encode_thread = Process(
                target=video.encode_output, args=(recorder.frame_counts, recorder.start_time, time.time(), recorder.fps, recorder.video_filename, "test.mp4"))
            encode_thread.start()


if __name__ == "__main__":
    cherrypy.quickstart(main_server, "/", {"/frame.jpg": {
                        "tools.staticfile.on": True, "tools.staticfile.filename": os.getcwd() + "/frame.jpg"}})
