import gstreamer
import cherrypy
import sqlite3 as sql
import tbapy
import shutil
import json
import threading
from pathlib import Path
import time
import subprocess
import os

# Config
port = 8000
host = "0.0.0.0"
db_path = "videos.db"
video_dir = "saved_videos"
usb_path = "/transfer-usb/"  # include trailing slash
schedule_csv = "schedule.csv"
tba = tbapy.TBA(
    "dfdifQQrVJfI7uRVhJzN21tEmB3zCne9CGHORrvz2M5jb5Gz53rUeCdpqCjz372N")

# Init recorder
recorder = gstreamer.GstreamerRecorder()
recorder.start(gstreamer.RecorderMode.IDLE)

# Create folder
if not os.path.exists(video_dir):
    os.mkdir(video_dir)

# Run command and get stout and sterr


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


# Init database
exists = Path(db_path).is_file()
conn = sql.connect(db_path)
cur = conn.cursor()
if not exists:
    cur.execute("DROP TABLE IF EXISTS videos")
    cur.execute("""CREATE TABLE videos (
        event TEXT,
        match INTEGER,
        filename TEXT,
        b1 INTEGER,
        b2 INTEGER,
        b3 INTEGER,
        r1 INTEGER,
        r2 INTEGER,
        r3 INTEGER
        ); """)
    cur.execute("DROP TABLE IF EXISTS usb")
    cur.execute("""CREATE TABLE usb (
        filename TEXT UNIQUE,
        to_copy INTEGER,
        to_delete INTEGER
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
    cur.execute("INSERT INTO config (key, value) VALUES ('usb_connected', '0')")
    cur.execute("INSERT INTO config (key, value) VALUES ('usb_used', '0')")
    cur.execute("INSERT INTO config (key, value) VALUES ('usb_total', '0')")
else:
    cur.execute("UPDATE config SET value=0 WHERE key='recording'")
conn.commit()
conn.close()


# USB management thread
def manage_usb():
    def usb_connected():
        return "disconnected.txt" not in os.listdir(usb_path)

    conn = sql.connect(db_path)
    cur = conn.cursor()

    while True:
        # Set disconnected
        cur.execute("UPDATE config SET value='0' WHERE key='usb_connected'")
        conn.commit()

        # Wait for connection
        while not usb_connected():
            time.sleep(1)

        # Set connected
        cur.execute("UPDATE config SET value='1' WHERE key='usb_connected'")
        conn.commit()

        # Wait for disconnect
        while usb_connected():
            # Get used and available space
            output = run_command(["df", usb_path]).split("\n")[1].split(" ")
            used = int(output[8])
            total = int(output[8]) + int(output[11])
            cur.execute(
                "UPDATE config SET value=? WHERE key='usb_used'", (used,))
            cur.execute(
                "UPDATE config SET value=? WHERE key='usb_total'", (total,))

            # Update file list
            cur.execute("DELETE FROM usb WHERE to_copy=0 AND to_delete=0")
            files = [x for x in os.listdir(usb_path) if x.endswith(".mp4")]
            for filename in files:
                try:
                    cur.execute(
                        "INSERT INTO usb(filename,to_copy,to_delete) VALUES (?,0,0)", (filename,))
                except:
                    pass

            # Commit db before copy
            conn.commit()

            # Copy files
            to_copy = [x[0] for x in cur.execute(
                "SELECT filename FROM usb WHERE to_copy=1").fetchall()]
            for filename in to_copy:
                try:
                    shutil.copyfile(video_dir + os.path.sep +
                                    filename, usb_path + filename)
                except:
                    pass
                else:
                    cur.execute(
                        "UPDATE usb SET to_copy=0 WHERE filename=?", (filename,))

            # Delete files
            to_delete = [x[0] for x in cur.execute(
                "SELECT filename FROM usb WHERE to_delete=1").fetchall()]
            for filename in to_delete:
                if Path(usb_path + filename).is_file():
                    try:
                        os.remove(usb_path + filename)
                    except:
                        pass
                    else:
                        cur.execute(
                            "DELETE FROM usb WHERE filename=?", (filename,))

            # Commit db
            conn.commit()

            time.sleep(1)


class main_server(object):
    @cherrypy.expose
    def index():
        return """
<html>

<head>
    <title>
        6328 Scout Video - Recording
    </title>
    <link rel="stylesheet" type="text/css" href="/static/css/index.css"></link>
    <script type="text/javascript" src="/static/js/index.js"></script>
    <link rel="shortcut icon" href="/static/img/favicon.ico"></link>
</head>

<body>
    <div class="flash-box fade-out" id="flashBox"></div>

    <div class="camera-view">
        <button onclick="javascript:reconnect()">
            Reconnect to camera
        </button>
        <img class="frame" src="frame.jpg" id="frame">
        <div class="time" id="time">
            00:00:00.0
        </div>
    </div>

    <a href="/videos">
        View Videos
    </a>
    <br>
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
    def reconnect():
        conn = sql.connect(db_path)
        cur = conn.cursor()
        recording = cur.execute(
            "SELECT value FROM config WHERE key='recording'").fetchall()[0][0]
        conn.commit()
        conn.close()

        if recording == "1":
            return "Cannot reconnect while recording."
        else:
            recorder.start(gstreamer.RecorderMode.IDLE)
            return "Camera successfully reconnected."

    @cherrypy.expose
    def start_recording(match=0):
        conn = sql.connect(db_path)
        cur = conn.cursor()
        cur.execute("UPDATE config SET value=? WHERE key='recording'", (match,))
        conn.commit()
        conn.close()

        recorder.start(gstreamer.RecorderMode.RECORD, "temp_" +
                       time.strftime("%Y-%m-%d_%H-%M-%S") + ".mp4")
        return

    @cherrypy.expose
    def stop_recording(save="1"):
        temp_filename = recorder.filename
        recorder.start(gstreamer.RecorderMode.IDLE)

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
            os.remove(temp_filename)
        else:
            destination = video_dir + os.path.sep + event + \
                "_m" + str(match).zfill(3) + ".mp4"
            cur.execute(
                "DELETE FROM videos WHERE match=? AND event=?", (match, event))
            cur.execute("INSERT INTO videos(event,match,filename,b1,b2,b3,r1,r2,r3) VALUES (?,?,?,?,?,?,?,?,?)",
                        (event, match, destination) + tuple(teams))

            os.rename(temp_filename, destination)

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
                "SELECT * FROM videos WHERE event=? AND match=?", (event, matches[i]["match"])).fetchall()
            if len(video_rows) < 1:
                matches[i]["status"] = "waiting"
            else:
                matches[i]["status"] = "finished"

        recording = int(cur.execute(
            "SELECT value FROM config WHERE key='recording'").fetchall()[0][0])
        if recording != 0:
            matches[recording - 1]["status"] = "recording"

        conn.close()
        return json.dumps(matches)

    @cherrypy.expose
    def videos():
        output = """
<html>

<head>
    <title>
        6328 Scout Video - Viewing
    </title>
    <link rel="stylesheet" type="text/css" href="/static/css/index.css"></link>
    <link rel="shortcut icon" href="/static/img/favicon.ico"></link>
</head>

<body>
    <div class="camera-view">
        <video controls autoplay style="width: 590px;" id="videoView" hidden>
    </div>
    Event:
    <select id="eventSelect">
        <option>
            All
        </option>
        $EVENT_OPTIONS
    </select>
    <br>
    Team:
    <input type="number" id="teamSelect">
    </input>
    <button onclick="javascript:search()">
        Search
    </button>

    <table id="matchTable" style="margin-top: 10px;">
        <tr>
            <th>
                Event
            </th>
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

    <script type="text/javascript" src="/static/js/videos.js"></script>
</body>

</html>
        """
        conn = sql.connect(db_path)
        cur = conn.cursor()

        events = [x[0] for x in cur.execute(
            "SELECT DISTINCT event FROM videos ORDER BY event").fetchall()]
        option_html = ""
        for event in events:
            option_html += "<option>" + event + "</option>"

        conn.close()
        return output.replace("$EVENT_OPTIONS", option_html)

    @cherrypy.expose
    def search(event="All", team="0"):
        conn = sql.connect(db_path)
        cur = conn.cursor()

        if event == "All":
            event = "%"
        if team == "0":
            team = "%"
        data = cur.execute(
            "SELECT * FROM videos WHERE event LIKE ? AND (b1 LIKE ? OR b2 LIKE ? OR b3 LIKE ? OR r1 LIKE ? OR r2 LIKE ? OR r3 LIKE ?) ORDER BY event, match", (event, team, team, team, team, team, team)).fetchall()
        data = [{
            "event": x[0],
            "match": x[1],
            "filename": x[2],
            "b1": x[3],
            "b2": x[4],
            "b3": x[5],
            "r1": x[6],
            "r2": x[7],
            "r3": x[8]
        } for x in data]

        conn.close()
        return json.dumps(data)


if __name__ == "__main__":
    usb_thread = threading.Thread(target=manage_usb, args=(), daemon=True)
    usb_thread.start()
    cherrypy.config.update(
        {'server.socket_port': port, 'server.socket_host': host})
    cherrypy.quickstart(main_server, "/", {"/frame.jpg": {
                        "tools.staticfile.on": True, "tools.staticfile.filename": os.getcwd() + "/frame.jpg"}, "/static": {"tools.staticdir.on": True, "tools.staticdir.dir": os.getcwd() + "/static"}, "/" + video_dir: {"tools.staticdir.on": True, "tools.staticdir.dir": os.getcwd() + os.path.sep + video_dir}})
