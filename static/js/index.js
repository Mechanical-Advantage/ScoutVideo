// Setup
var recording = false
var startTime = 0
var flashesDone = 0
const flashTime = 180 // seconds
const flashRate = 20 // seconds

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

// Get starting matches
matches = []
function getMatches() {
    request("GET", "/get_matches", function (data) {
        matches = JSON.parse(data)

        var table = document.getElementById("matchTable")
        while (table.children.length > 1) {
            table.removeChild(table.children[1])
        }
        for (var i = 0; i < matches.length; i++) {
            var row = document.createElement("TR")

            // Match number
            row.appendChild(document.createElement("TD"))
            row.firstChild.classList.add("data")
            row.firstChild.innerHTML = matches[i]["match"]

            // Teams
            for (var f = 0; f < 6; f++) {
                var cell = document.createElement("TD")
                cell.classList.add("data")
                cell.classList.add(f < 3 ? "blue" : "red")
                cell.innerHTML = matches[i]["teams"][f]
                row.appendChild(cell)
            }

            // Buttons
            var buttonCell = document.createElement("TD")
            row.appendChild(buttonCell)

            // Start button and check
            buttonCell.appendChild(document.createElement("DIV"))
            buttonCell.firstChild.hidden = true
            buttonCell.firstChild.appendChild(document.createElement("BUTTON"))
            buttonCell.firstChild.firstChild.innerHTML = "\u{1f3ac}"
            function startFunc(match) {
                return function () {
                    startRecording(match)
                }
            }
            buttonCell.firstChild.firstChild.onclick = startFunc(matches[i]["match"])
            buttonCell.firstChild.firstChild.classList.add("emoji")
            buttonCell.firstChild.appendChild(document.createElement("SPAN"))
            buttonCell.firstChild.lastChild.innerHTML = "\u{2705}"
            buttonCell.firstChild.lastChild.classList.add("emoji")

            // Stop button and trash can
            buttonCell.appendChild(document.createElement("DIV"))
            buttonCell.lastChild.hidden = true
            buttonCell.lastChild.appendChild(document.createElement("BUTTON"))
            buttonCell.lastChild.firstChild.innerHTML = "\u{1f6d1}"
            function stopFunc(match, save) {
                return function () {
                    stopRecording(match, save)
                }
            }
            buttonCell.lastChild.firstChild.onclick = stopFunc(matches[i]["match"], true)
            buttonCell.lastChild.firstChild.classList.add("emoji")
            buttonCell.lastChild.appendChild(document.createElement("BUTTON"))
            buttonCell.lastChild.lastChild.innerHTML = "\u{1f5d1}"
            buttonCell.lastChild.lastChild.onclick = stopFunc(matches[i]["match"], false)
            buttonCell.lastChild.lastChild.classList.add("emoji")

            // Loading symbol
            buttonCell.appendChild(document.createElement("DIV"))
            buttonCell.lastChild.hidden = true
            buttonCell.lastChild.classList.add("loading")
            buttonCell.lastChild.appendChild(document.createElement("IMG"))
            buttonCell.lastChild.firstChild.classList.add("loading")
            buttonCell.lastChild.firstChild.src = "/static/img/loading.gif"

            // Show the correct buttons
            if (matches[i]["status"] == "waiting") {
                buttonCell.firstChild.hidden = false
                buttonCell.firstChild.lastChild.hidden = true
            } else if (matches[i]["status"] == "recording") {
                buttonCell.children[1].hidden = false
                recording = true
                flashesDone = 0
            } else if (matches[i]["status"] == "finished") {
                buttonCell.firstChild.hidden = false
                buttonCell.firstChild.lastChild.hidden = false
            }

            table.appendChild(row)
            matches[i]["row"] = row
        }

    }, {}, "Failed to load matches.")
}
getMatches()

// Load schedule    
function loadSchedule(src) {
    event = document.getElementById("event").value
    request("POST", "/set_event", function (data) {
        alert(data)
        getMatches()
    }, {
        event: event,
        source: src
    }, "Failed to contact server.")
}

// Start recording
function startRecording(match) {
    if (recording) {
        alert("You cannot record multiple matches at once.")
    } else {
        matches[match - 1]["row"].lastChild.firstChild.hidden = true
        matches[match - 1]["row"].lastChild.lastChild.hidden = false
        request("POST", "/start_recording", function () {
            recording = true
            matches[match - 1]["row"].lastChild.children[1].hidden = false
            matches[match - 1]["row"].lastChild.lastChild.hidden = true
            flashesDone = 0
            startTime = new Date().getTime()
        }, {
            match: match
        }, "Failed to contact server.")
    }
}


// Stop recording
function stopRecording(match, save) {
    if (confirm(save ? "Are you sure you want to stop recording?" : "Are you sure you want to cancel recording? It will be lost forever.")) {
        matches[match - 1]["row"].lastChild.lastChild.hidden = false
        matches[match - 1]["row"].lastChild.children[1].hidden = true
        request("POST", "/stop_recording", function () {
            recording = false
            matches[match - 1]["row"].lastChild.lastChild.hidden = true
            matches[match - 1]["row"].lastChild.firstChild.hidden = false
            if (save) {
                matches[match - 1]["row"].lastChild.firstChild.lastChild.hidden = false
            }
        }, {
            save: save ? "1" : "0"
        }, "Failed to contact server.")
    }
}

// Reconnect to camera
function reconnect() {
    request("POST", "/reconnect", function (data) {
        alert(data)
    }, {}, "Failed to contact server.")
}

// Refresh frame
setInterval(function () {
    document.getElementById("frame").src = "frame.jpg?time=" + new Date().getTime().toString()
}, 250)

// Manager timer
setInterval(function () {
    var time = document.getElementById("time")
    time.hidden = !recording

    if (recording) {
        var elapsed = new Date().getTime() - startTime
        var hours = Math.floor(elapsed / 3600000)
        var remaining = elapsed % 3600000
        var minutes = Math.floor(remaining / 60000)
        remaining = remaining % 60000
        var seconds = Math.floor(remaining / 1000)
        var tenths = Math.floor((remaining % 1000) / 100)

        time.innerHTML = hours.toString().padStart(2, "0") + ":" + minutes.toString().padStart(2, "0") + ":" + seconds.toString().padStart(2, "0") + "." + tenths.toString()

        var currentFlash = Math.floor((elapsed - (flashTime * 1000)) / (flashRate * 1000)) + 1
        if (currentFlash > flashesDone) {
            flashesDone = currentFlash
            flash(3)
        }
    }
}, 100)

// Flash screen when recording for too long
function flash(times) {
    var flashBox = document.getElementById("flashBox")
    flashBox.classList.remove("fade-out")
    flashBox.style.opacity = 1
    setTimeout(function () {
        flashBox.classList.add("fade-out")
        flashBox.style.opacity = 0
        if (times > 1) {
            setTimeout(function () {
                flash(times - 1)
            }, 400)
        }
    }, 100)
}