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
usb_paths = {
    "/transfer-black/": "black",
    "/transfer-darkblue/": "darkblue",
    "/transfer-skyblue/": "skyblue",
    "/transfer-gray/": "gray",
    "/transfer-green/": "green",
    "/transfer-purple/": "purple",
    "/transfer-red/": "red"
}
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
        match TEXT,
        match_sortid INTEGER,
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
        size INTEGER,
        to_copy INTEGER,
        to_delete INTEGER
        ); """)
    cur.execute("DROP TABLE IF EXISTS schedule")
    cur.execute("""CREATE TABLE schedule (
        match TEXT,
        match_sortid INTEGER,
        editable INTEGER,
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
    cur.execute("INSERT INTO config (key, value) VALUES ('usb_name', '')")
    cur.execute("INSERT INTO config (key, value) VALUES ('usb_used', '0')")
    cur.execute("INSERT INTO config (key, value) VALUES ('usb_total', '0')")
else:
    cur.execute("UPDATE config SET value=0 WHERE key='recording'")
conn.commit()
conn.close()


# USB management thread
current_usb_path = ""
current_usb_name = ""


def manage_usb():
    global current_usb_path
    global current_usb_name

    def usb_connected(path):
        try:
            return "disconnected.txt" not in os.listdir(path)
        except:
            return False

    conn = sql.connect(db_path)
    cur = conn.cursor()

    while True:
        # Set disconnected
        cur.execute("UPDATE config SET value='0' WHERE key='usb_connected'")
        conn.commit()

        # Wait for connection
        connected = False
        while not connected:
            time.sleep(0.2)
            for path, name in usb_paths.items():
                if usb_connected(path):
                    connected = True
                    current_usb_path = path
                    current_usb_name = name
                    break

        # Set connected
        cur.execute("UPDATE config SET value='1' WHERE key='usb_connected'")
        cur.execute("UPDATE config SET value=? WHERE key='usb_name'",
                    (current_usb_name,))
        conn.commit()

        # Wait for disconnect
        while usb_connected(current_usb_path):
            try:
                # Get used and available space
                output = run_command(["df", current_usb_path]).split("\n")[
                    1].split(" ")
                used = int(output[8])
                total = int(output[7])
                cur.execute(
                    "UPDATE config SET value=? WHERE key='usb_used'", (used,))
                cur.execute(
                    "UPDATE config SET value=? WHERE key='usb_total'", (total,))

                # Update file list
                cur.execute("DELETE FROM usb WHERE to_copy=0 AND to_delete=0")
                files = [x for x in os.listdir(
                    current_usb_path) if x.endswith(".mp4")]
                for filename in files:
                    try:
                        size = round(
                            os.stat(current_usb_path + filename).st_size / 1024)
                        cur.execute(
                            "INSERT INTO usb(filename,size,to_copy,to_delete) VALUES (?,?,0,0)", (filename, size))
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
                                        filename, current_usb_path + filename)
                    except:
                        pass
                    else:
                        cur.execute(
                            "UPDATE usb SET to_copy=0 WHERE filename=?", (filename,))

                # Delete files
                to_delete = [x[0] for x in cur.execute(
                    "SELECT filename FROM usb WHERE to_delete=1").fetchall()]
                for filename in to_delete:
                    if Path(current_usb_path + filename).is_file():
                        run_command(
                            ["rm", current_usb_path + filename], output=False)
                        cur.execute(
                            "DELETE FROM usb WHERE filename=?", (filename,))

                # Commit db
                conn.commit()

                time.sleep(0.2)
            except:
                pass


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

    <a href="/videos" target="_blank">
        View Videos
    </a>

    <br>
    <b>
        Enter event name:
    </b>
    <input type="text" id="event">

    <br>
    <b>
        # of practice matches:
    </b>
    <input type="number" id="practiceMatches" min=0>

    <br>
    <b>
        Include playoffs:
    </b>
    <input type="checkbox" id="includePlayoffs">

    <div style="margin-top: 5px;">
        <button onclick="javascript:loadSchedule(&quot;tba&quot;)">
            Load from TBA
        </button>
        <button onclick="javascript:loadSchedule(&quot;csv&quot;)">
            Load from CSV
        </button>
    </div>

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
    def start_recording(match=""):
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
        sortid = cur.execute(
            "SELECT match_sortid FROM schedule WHERE match=?", (match,)).fetchall()[0][0]
        teams = cur.execute(
            "SELECT b1,b2,b3,r1,r2,r3 FROM schedule WHERE match=?", (match,)).fetchall()[0]
        cur.execute("UPDATE config SET value=0 WHERE key='recording'")

        if save == "0":
            os.remove(temp_filename)
        else:
            destination = video_dir + os.path.sep + match + \
                " (" + ",".join([str(x) for x in teams]) + ").mp4"
            cur.execute(
                "DELETE FROM videos WHERE match=?", (match,))
            cur.execute("INSERT INTO videos(event,match,match_sortid,filename,b1,b2,b3,r1,r2,r3) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (event, match, sortid, destination) + tuple(teams))

            os.rename(temp_filename, destination)

        conn.commit()
        conn.close()
        return

    @cherrypy.expose
    def set_event(event="2017nhgrs", source="tba", practice="0", playoffs="0"):
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
                        [match_raw.key, match_raw.match_number, 0, b1, b2, b3, r1, r2, r3])
        else:
            # Get from csv
            try:
                csv = open(schedule_csv, "r")
            except:
                conn.close()
                return "Failed to open csv file."
            matches = [row.split(",") for row in csv.read().split("\n")][:-1]
            for i in range(len(matches)):
                matches[i].insert(1, i + 1)
                matches[i].insert(2, 0)
            try:
                x = 0
            except:
                conn.close()
                return "Failed to parse csv file."
            csv.close()

        # Add practice matches
        if int(practice) != 0:
            for i in range(int(practice)):
                match_number = int(practice) - i
                matches.insert(
                    0, [event + "_pm" + str(match_number), (i + 1) * -1, 1, 0, 0, 0, 0, 0, 0])

        # Add playoff matches
        playoff_matches = [
            "qf1m1",
            "qf2m1",
            "qf3m1",
            "qf4m1",
            "qf1m2",
            "qf2m2",
            "qf3m2",
            "qf4m2",
            "qf1m3",
            "qf2m3",
            "qf3m3",
            "qf4m3",
            "sf1m1",
            "sf2m1",
            "sf1m2",
            "sf2m2",
            "sf1m3",
            "sf2m3",
            "f1m1",
            "f1m2",
            "f1m3"
        ]
        if playoffs == "1":
            sortid = 999
            for match_code in playoff_matches:
                sortid += 1
                matches.append([event + "_" + match_code,
                                sortid, 1, 0, 0, 0, 0, 0, 0])

        # Save to db
        cur.execute("DELETE FROM schedule")
        cur.execute(
            "UPDATE config SET value=? WHERE key='event_cached'", (event,))
        for match in matches:
            try:
                cur.execute(
                    "INSERT INTO schedule(match,match_sortid,editable,b1,b2,b3,r1,r2,r3) VALUES (?,?,?,?,?,?,?,?,?)", tuple(match))
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
            "editable": x[1],
            "teams": x[2:8],
            "status": "unknown"
        } for x in cur.execute("SELECT match,editable,b1,b2,b3,r1,r2,r3 FROM schedule ORDER BY match_sortid").fetchall()]

        for i in range(len(matches)):
            video_rows = cur.execute(
                "SELECT * FROM videos WHERE match=?", (matches[i]["match"],)).fetchall()
            if len(video_rows) < 1:
                matches[i]["status"] = "waiting"
            else:
                matches[i]["status"] = "finished"

        recording = cur.execute(
            "SELECT value FROM config WHERE key='recording'").fetchall()[0][0]
        if recording != "0":
            for i in matches:
                if i["match"] == recording:
                    i["status"] = "recording"

        conn.close()
        return json.dumps(matches)

    @cherrypy.expose
    def update_teams(match, b1, b2, b3, r1, r2, r3):
        conn = sql.connect(db_path)
        cur = conn.cursor()

        cur.execute("UPDATE schedule SET b1=?, b2=?, b3=?, r1=?, r2=?, r3=? WHERE match=?",
                    (b1, b2, b3, r1, r2, r3, match))

        conn.commit()
        conn.close()
        return

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
            Video playback not supported
        </video>
        <h3>
            USB Drive Files
        </h3>

        <div id="usbConnected" style="text-decoration: underline; margin-bottom: 5px;">
            Disconnected
        </div>

        <button style="margin-top: 5px; margin-bottom: 5px;" onclick="javascript:unmount()">
            Eject USB drive
        </button>

        <div style="font-style: italic;">
            <span id="usbUsed">?</span> GB/<span id="usbTotal">?</span> GB
        </div>
        <progress value="0" max="100" id="usbProgress"></progress>

        <table id="usbTable">
            <tr>
                <th>
                    Filename
                </th>
                <th>
                    Size
                </th>
            </tr>
        </table>
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
            "SELECT match,filename,b1,b2,b3,r1,r2,r3 FROM videos WHERE event LIKE ? AND (b1 LIKE ? OR b2 LIKE ? OR b3 LIKE ? OR r1 LIKE ? OR r2 LIKE ? OR r3 LIKE ?) ORDER BY event, match_sortid", (event, team, team, team, team, team, team)).fetchall()
        data = [{
            "match": x[0],
            "filename": x[1],
            "b1": x[2],
            "b2": x[3],
            "b3": x[4],
            "r1": x[5],
            "r2": x[6],
            "r3": x[7]
        } for x in data]

        conn.close()
        return json.dumps(data)

    @cherrypy.expose
    def get_files():
        conn = sql.connect(db_path)
        cur = conn.cursor()

        data = cur.execute(
            "SELECT value FROM config WHERE key='usb_used' OR key='usb_total' OR key='usb_connected' OR key='usb_name' ORDER BY key").fetchall()
        connected = data[0][0] == "1"
        name = data[1][0]
        total = data[2][0]
        used = data[3][0]

        file_data = cur.execute(
            "SELECT filename,size,to_copy FROM usb WHERE to_delete=0 ORDER BY filename").fetchall()

        file_data = [{
            "filename": x[0],
            "size": x[1],
            "to_copy": x[2]
        } for x in file_data]
        result = {
            "used": used,
            "total": total,
            "connected": connected,
            "name": name,
            "files": file_data
        }

        conn.close()
        return json.dumps(result)

    @cherrypy.expose
    def unmount_usb():
        run_command(["sync"], output=False)
        run_command(["sudo", "umount", current_usb_path])

    @cherrypy.expose
    def copy_file(filename=""):
        conn = sql.connect(db_path)
        cur = conn.cursor()

        filename = filename[len(video_dir) + len(os.path.sep):]
        cur.execute(
            "INSERT INTO usb(filename,to_copy,to_delete) VALUES (?,1,0)", (filename,))

        conn.commit()
        conn.close()

    @cherrypy.expose
    def delete_file(filename=""):
        conn = sql.connect(db_path)
        cur = conn.cursor()

        cur.execute("UPDATE usb SET to_delete=1 WHERE filename=?", (filename,))

        conn.commit()
        conn.close()

    @cherrypy.expose
    def shutdown():
        return """
<html>

<head>
    <title>
        6328 Scout Video - Shutdown
    </title>
    <link rel="stylesheet" type="text/css" href="/static/css/index.css"></link>
    <link rel="shortcut icon" href="/static/img/favicon.ico"></link>
    <script>

function request(method, url, response, data, error) {
    if (data == undefined) {
        data = {}
    }

    const http = new XMLHttpRequest()
    const form = new FormData()
    for (name in data) {
        form.append(name, data[name])
    }

    if (response != undefined) {
        http.onreadystatechange = function () {
            if (this.readyState == 4) {
                if (this.status == 200) {
                    response(this.responseText)
                } else {
                    if (error != undefined) {
                        console.error(error)
                        alert(error)
                    }
                }
            }
        }
    }

    if (error != undefined) {
        http.onerror = function () {
            console.error(error)
            alert(error)
        }

        http.ontimeout = function () {
            console.error(error)
            alert(error)
        }
    }

    http.open(method, url)
    http.send(form)
}

function send(func) {
    if (confirm("Are you sure you want to " + func + "?")) {
        request("POST", "/shutdown_internal", function () { }, {
                "func": func
            })
    }
}

    </script>
</head>

<body>
    <h4>
        Shutdown or Reboot Jetson:
    </h4>
    <button onclick="javascript:send(&quot;shutdown&quot;)">
        Shutdown
    </button>
    <button onclick="javascript:send(&quot;reboot&quot;)">
        Reboot
    </button>
</body>

</html>
        """

    @cherrypy.expose
    def shutdown_internal(func="none"):
        if func == "shutdown":
            run_command(["sudo", "shutdown", "now"])
        elif func == "reboot":
            run_command(["sudo", "reboot"])
        return ""


if __name__ == "__main__":
    usb_thread = threading.Thread(target=manage_usb, args=(), daemon=True)
    usb_thread.start()
    cherrypy.config.update(
        {'server.socket_port': port, 'server.socket_host': host})
    cherrypy.quickstart(main_server, "/", {"/frame.jpg": {
                        "tools.staticfile.on": True, "tools.staticfile.filename": os.getcwd() + "/frame.jpg"}, "/static": {"tools.staticdir.on": True, "tools.staticdir.dir": os.getcwd() + "/static"}, "/" + video_dir: {"tools.staticdir.on": True, "tools.staticdir.dir": os.getcwd() + os.path.sep + video_dir}})
