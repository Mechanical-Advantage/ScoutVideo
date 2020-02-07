import video
import cherrypy
from simple_websocket_server import WebSocketServer, WebSocket
import sqlite3 as sql
import tbapy
import json
import threading
from multiprocessing import Process
from pathlib import Path
import time
import os

# Config
port = 8080
socket_port = 8081
host = "0.0.0.0"
db_path = "videos.db"
video_dir = "videos"
schedule_csv = "schedule.csv"
tba = tbapy.TBA(
    "dfdifQQrVJfI7uRVhJzN21tEmB3zCne9CGHORrvz2M5jb5Gz53rUeCdpqCjz372N")

# Init recorder
recorder = video.VideoRecorder(start_thread=True)

# Create folder
if not os.path.exists(video_dir):
    os.mkdir(video_dir)

# Init database
if not Path(db_path).is_file():
    conn = sql.connect(db_path)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS videos")
    cur.execute("""CREATE TABLE videos (
        event TEXT,
        match INTEGER,
        filename TEXT,
        encoded INTEGER,
        b1 INTEGER,
        b2 INTEGER,
        b3 INTEGER,
        r1 INTEGER,
        r2 INTEGER,
        r3 INTEGER
        ); """)
    cur.execute("DROP TABLE IF EXISTS schedule")
    cur.execute("""CREATE TABLE schedule (
        match INTEGER,
        b1 INTEGER,
        b2 INTEGER,
        b3 INTEGER,
        r1 INTEGER,
        r2 INTEGER,
        r3 INTEGER
        ); """)
    cur.execute("DROP TABLE IF EXISTS config")
    cur.execute("""CREATE TABLE config (
        key TEXT,
        value TEXT
        ); """)
    cur.execute("INSERT INTO config (key, value) VALUES ('event', '2017nhgrs')")
    cur.execute("INSERT INTO config (key, value) VALUES ('recording', '0')")
    conn.commit()
    conn.close()


# Encoder thread
def encode_thread(frame_count, start_time, stop_time, fps, input, event, match):
    filename = video_dir + os.path.sep + event + \
        "_m" + str(match).zfill(3) + ".mp4"
    if Path(filename).is_file():
        os.remove(filename)
    video.encode_output(frame_count, start_time,
                        stop_time, fps, input, filename)
    conn = sql.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE videos SET filename=?, encoded=1 WHERE event=? AND match=?", (filename, event, match))
    conn.commit()
    conn.close()
    send_complete(match)


class main_server(object):
    @cherrypy.expose
    def index():
        return """
<html>

<head>
    <title>
        6328 Scout Video
    </title>
    <link rel="stylesheet" type="text/css" href="/static/css/index.css"></link>
    <script type="text/javascript" src="/static/js/index.js"></script>
    <link rel="shortcut icon" href="/static/img/favicon.ico"></link>
</head>

<body>
    <div class="flash-box fade-out" id="flashBox"></div>

    <div class="camera-view">
        <img class="frame" src="frame.jpg" id="frame">
        <div class="time" id="time">
            00:00:00.0
        </div>
    </div>
 
    <b>
        Enter event name:
    </b> 
    <input type="text" id="event">
    <button onclick="javascript:loadSchedule(&quot;tba&quot;)">
        Load from TBA
    </button>
    <button onclick="javascript:loadSchedule(&quot;csv&quot;)">
        Load from CSV
    </button>
                    
    <table id="matchTable" style="margin-top: 10px;">
        <tr>
            <th>
                Match
            </th>
            <th>
                B1
            </th>
            <th>
                B2
            </th>
            <th>
                B3
            </th>
            <th>
                R1
            </th>
            <th>
                R2
            </th>
            <th>
                R3
            </th>
        </tr>
    </table>
</body>

</html>
        """

    @cherrypy.expose
    def start_recording(match=0):
        conn = sql.connect(db_path)
        cur = conn.cursor()
        cur.execute("UPDATE config SET value=? WHERE key='recording'", (match,))
        conn.commit()
        conn.close()

        if recorder.open:
            recorder.stop()
        recorder.start()
        return

    @cherrypy.expose
    def stop_recording(save="1"):
        if recorder.open:
            recorder.stop()

            conn = sql.connect(db_path)
            cur = conn.cursor()
            match = cur.execute(
                "SELECT value FROM config WHERE key='recording'").fetchall()[0][0]
            event = cur.execute(
                "SELECT value FROM config WHERE key='event'").fetchall()[0][0]
            teams = cur.execute(
                "SELECT b1,b2,b3,r1,r2,r3 FROM schedule WHERE match=?", (match,)).fetchall()[0]
            cur.execute("UPDATE config SET value=0 WHERE key='recording'")

            if save == "0":
                os.remove(recorder.video_filename)
            else:
                cur.execute(
                    "DELETE FROM videos WHERE match=? AND event=?", (match, event))
                cur.execute("INSERT INTO videos(event,match,encoded,b1,b2,b3,r1,r2,r3) VALUES (?,?,?,?,?,?,?,?,?)",
                            (event, match, 0) + tuple(teams))

                # Start encoding
                thread = threading.Thread(target=encode_thread, args=(
                    recorder.frame_counts,
                    recorder.start_time,
                    recorder.end_time,
                    recorder.fps,
                    recorder.video_filename,
                    event,
                    match
                ))
                thread.start()

            conn.commit()
            conn.close()
        return

    @cherrypy.expose
    def set_event(event="2017nhgrs", source="tba"):
        conn = sql.connect(db_path)
        cur = conn.cursor()
        cur.execute("UPDATE config SET value=? WHERE key='event'", (event,))

        if source == "tba":
            # Get from the blue alliace
            try:
                matchlist_raw = tba.event_matches(event)
                matchlist_raw.sort(key=lambda x: x.match_number)
            except:
                return "Error - could not retrieve schedule"

            if len(matchlist_raw) == 0:
                return "Error - no schedule available"

            matches = []
            for match_raw in matchlist_raw:
                if match_raw.comp_level == "qm":
                    b1 = match_raw.alliances["blue"]["team_keys"][0][3:]
                    b2 = match_raw.alliances["blue"]["team_keys"][1][3:]
                    b3 = match_raw.alliances["blue"]["team_keys"][2][3:]
                    r1 = match_raw.alliances["red"]["team_keys"][0][3:]
                    r2 = match_raw.alliances["red"]["team_keys"][1][3:]
                    r3 = match_raw.alliances["red"]["team_keys"][2][3:]
                    matches.append(
                        [match_raw.match_number, b1, b2, b3, r1, r2, r3])
        else:
            # Get from csv
            try:
                csv = open(schedule_csv, "r")
            except:
                conn.close()
                return "Failed to open csv file."
            matches = [row.split(",") for row in csv.read().split("\n")]
            try:
                x = 0
            except:
                conn.close()
                return "Failed to parse csv file."
            csv.close()

        cur.execute("DELETE FROM schedule")
        cur.execute(
            "UPDATE config SET value=? WHERE key='event_cached'", (event,))
        for match in matches:
            try:
                cur.execute(
                    "INSERT INTO schedule(match,b1,b2,b3,r1,r2,r3) VALUES (?,?,?,?,?,?,?)", tuple(match))
            except:
                conn.close()
                return "Failed to save schedule data."

        conn.commit()
        conn.close()
        return "Saved schedule for " + event + "."

    @cherrypy.expose
    def get_matches():
        conn = sql.connect(db_path)
        cur = conn.cursor()

        event = cur.execute(
            "SELECT value FROM config WHERE key='event'").fetchall()[0][0]
        matches = [{
            "match": x[0],
            "teams": x[1:7],
            "status": "unknown"
        } for x in cur.execute("SELECT * FROM schedule ORDER BY match").fetchall()]

        for i in range(len(matches)):
            video_rows = cur.execute(
                "SELECT encoded FROM videos WHERE event=? AND match=?", (event, matches[i]["match"])).fetchall()
            if len(video_rows) < 1:
                matches[i]["status"] = "waiting"
            else:
                if video_rows[0][0] == 1:
                    matches[i]["status"] = "finished"
                else:
                    matches[i]["status"] = "encoding"

        recording = int(cur.execute(
            "SELECT value FROM config WHERE key='recording'").fetchall()[0][0])
        if recording != 0:
            matches[recording - 1]["status"] = "recording"

        conn.close()
        return json.dumps(matches)


# Finish web socket server
clients = []


def send_complete(match):
    for client in clients:
        client.send_message(str(match))
        cherrypy.log("Sent data '" + str(match) +
                     "' to " + client.address[0])


class finish_server(WebSocket):
    global clients

    def handle(self):
        cherrypy.log("Received data '" + self.data +
                     "' from " + self.address[0])

    def connected(self):
        cherrypy.log("Socket opened from " + self.address[0])
        clients.append(self)

    def handle_close(self):
        cherrypy.log("Socket closed to " + self.address[0])
        clients.remove(self)


def run_socket_server():
    server = WebSocketServer(host, socket_port, finish_server)
    cherrypy.log("Starting web socket server on ws://" +
                 host + ":" + str(socket_port))
    server.serve_forever()
    cherrypy.log("Stopping web socket server on ws://" +
                 host + ":" + str(socket_port))


if __name__ == "__main__":
    server_thread = threading.Thread(target=run_socket_server, daemon=True)
    server_thread.start()
    cherrypy.config.update(
        {'server.socket_port': port, 'server.socket_host': host})
    cherrypy.quickstart(main_server, "/", {"/frame.jpg": {
                        "tools.staticfile.on": True, "tools.staticfile.filename": os.getcwd() + "/frame.jpg"}, "/static": {"tools.staticdir.on": True, "tools.staticdir.dir": os.getcwd() + "/static"}})
