import gstreamer
import cherrypy
import sqlite3 as sql
import tbapy
import json
import threading
from pathlib import Path
import time
import os

# Config
port = 8080
host = "0.0.0.0"
db_path = "videos.db"
video_dir = "videos"
schedule_csv = "schedule.csv"
tba = tbapy.TBA(
    "dfdifQQrVJfI7uRVhJzN21tEmB3zCne9CGHORrvz2M5jb5Gz53rUeCdpqCjz372N")

# Init recorder
recorder = gstreamer.GstreamerRecorder()
recorder.start(gstreamer.RecorderMode.IDLE)

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
        saved INTEGER,
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

        recorder.start(gstreamer.RecorderMode.RECORD, "temp_" +
                       time.strftime("%Y-%m-%d_%H-%M-%S") + ".mp4")
        return

    @cherrypy.expose
    def stop_recording(save="1"):
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
            os.remove(recorder.get_filename())
        else:
            cur.execute(
                "DELETE FROM videos WHERE match=? AND event=?", (match, event))
            cur.execute("INSERT INTO videos(event,match,saved,b1,b2,b3,r1,r2,r3) VALUES (?,?,?,?,?,?,?,?,?)",
                        (event, match, 0) + tuple(teams))

            destination = video_dir + os.path.sep + event + \
                "_m" + str(match).zfill(3) + ".mp4"
            os.replace(recorder.get_filename(), destination)

            cur.execute(
                "UPDATE videos SET filename=?, saved=1 WHERE event=? AND match=?", (filename, event, match))

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
                "SELECT saved FROM videos WHERE event=? AND match=?", (event, matches[i]["match"])).fetchall()
            if len(video_rows) < 1:
                matches[i]["status"] = "waiting"
            else:
                if video_rows[0][0] == 1:
                    matches[i]["status"] = "finished"
                else:
                    matches[i]["status"] = "error"

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
    <script type="text/javascript" src="/static/js/videos.js"></script>
    <link rel="shortcut icon" href="/static/img/favicon.ico"></link>
</head>

<body>
    <div class="camera-view">
        <video src="http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4" controls style="width: 590px;">
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
</body>

</html>
        """
        # <button class="emoji">&#x25b6</button>
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
        print(event, team)
        conn = sql.connect(db_path)
        cur = conn.cursor()

        if event == "All":
            event = "%"
        if team == "0":
            team = "%"
        data = cur.execute(
            "SELECT * FROM videos WHERE event LIKE ? AND saved=1 AND (b1 LIKE ? OR b2 LIKE ? OR b3 LIKE ? OR r1 LIKE ? OR r2 LIKE ? OR r3 LIKE ?) ORDER BY event, match", (event, team, team, team, team, team, team)).fetchall()
        data = [{
            "event": x[0],
            "match": x[1],
            "filename": x[2],
            "b1": x[4],
            "b2": x[5],
            "b3": x[6],
            "r1": x[7],
            "r2": x[8],
            "r3": x[9]
        } for x in data]

        conn.close()
        return json.dumps(data)


if __name__ == "__main__":
    cherrypy.config.update(
        {'server.socket_port': port, 'server.socket_host': host})
    cherrypy.quickstart(main_server, "/", {"/frame.jpg": {
                        "tools.staticfile.on": True, "tools.staticfile.filename": os.getcwd() + "/frame.jpg"}, "/static": {"tools.staticdir.on": True, "tools.staticdir.dir": os.getcwd() + "/static"}})
