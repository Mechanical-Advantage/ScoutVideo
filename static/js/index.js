// Setup
recording = false

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
            } else if (matches[i]["status"] == "encoding") {
                buttonCell.lastChild.hidden = false
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
        matches[match - 1]["row"].lastChild.children[1].hidden = false
        recording = true
        // Tell the server to start recording
    }
}

// Stop recording
function stopRecording(match, save) {
    if (confirm(save ? "Are you sure you want to stop recording?" : "Are you sure you want to cancel recording? It will be lost forever.")) {
        matches[match - 1]["row"].lastChild.children[1].hidden = true
        matches[match - 1]["row"].lastChild.lastChild.hidden = false
        recording = false
        // Tell the server to stop recording
    }
}

// Refresh frame
setInterval(function () {
    document.getElementById("frame").src = "frame.jpg?time=" + new Date().getTime().toString()
}, 250)