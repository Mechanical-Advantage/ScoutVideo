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

// Search and reconstruct table
function search() {
    var event = document.getElementById("eventSelect").value
    var team = Number(document.getElementById("teamSelect").value)
    request("POST", "/search", function (data) {
        var matches = JSON.parse(data)
        var table = document.getElementById("matchTable")
        while (table.children.length > 1) {
            table.removeChild(table.children[1])
        }
        for (var i = 0; i < matches.length; i++) {
            var row = document.createElement("TR")

            // Match number
            row.appendChild(document.createElement("TD"))
            row.lastChild.classList.add("data")
            row.lastChild.innerHTML = matches[i]["match"]

            // Teams
            const positions = ["b1", "b2", "b3", "r1", "r2", "r3"]
            for (var f = 0; f < 6; f++) {
                var cell = document.createElement("TD")
                cell.classList.add("data")
                cell.classList.add(f < 3 ? "blue" : "red")
                cell.innerHTML = matches[i][positions[f]]
                row.appendChild(cell)
            }

            // Buttons
            var buttonCell = document.createElement("TD")
            row.appendChild(buttonCell)
            var buttonDiv = document.createElement("DIV")
            buttonCell.appendChild(buttonDiv)

            // Play button
            buttonDiv.appendChild(document.createElement("BUTTON"))
            buttonDiv.firstChild.innerHTML = "\u{25b6}"
            function startFunc(filename) {
                return function () {
                    var video = document.getElementById("videoView")
                    video.src = filename
                    video.hidden = false
                }
            }
            buttonDiv.firstChild.onclick = startFunc(matches[i]["filename"])
            buttonDiv.firstChild.classList.add("emoji")

            // Copy button
            buttonDiv.appendChild(document.createElement("BUTTON"))
            buttonDiv.lastChild.innerHTML = "\u{2709}"
            function copyFunc(filename) {
                return function () {
                    request("POST", "/copy_file", function () {
                        getFiles()
                    }, {
                        "filename": filename,
                    }, "Failed to copy file.")
                }
            }
            buttonDiv.lastChild.onclick = copyFunc(matches[i]["filename"])
            buttonDiv.lastChild.classList.add("emoji")

            table.appendChild(row)
        }
    }, {
        event: event,
        team: team
    }, "Failed to retrieve data.")
}
search()

// Get files and reconstruct files table
function getFiles() {
    request("GET", "/get_files", function (data) {
        var data = JSON.parse(data)

        // Connected
        document.getElementById("usbConnected").innerHTML = data.connected ? "Connected" : "Disconnected"

        // Progress bar
        document.getElementById("usbProgress").value = data.used
        document.getElementById("usbProgress").max = data.total
        document.getElementById("usbProgress").classList = [data.name]
        document.getElementById("usbUsed").innerHTML = Math.round((data.used / 1048576) * 10) / 10
        document.getElementById("usbTotal").innerHTML = Math.round((data.total / 1048576) * 10) / 10

        // File list
        var files = data.files
        var table = document.getElementById("usbTable")
        while (table.children.length > 1) {
            table.removeChild(table.children[1])
        }
        for (var i = 0; i < files.length; i++) {
            var row = document.createElement("TR")

            // File name
            row.appendChild(document.createElement("TD"))
            row.lastChild.classList.add("data")
            row.lastChild.innerHTML = files[i]["filename"]

            // Size
            row.appendChild(document.createElement("TD"))
            row.lastChild.classList.add("data")
            if (files[i]["size"] == null) {
                row.lastChild.innerHTML = "NA"
            } else {
                row.lastChild.innerHTML = (Math.round((files[i]["size"] / 1024) * 10) / 10).toString() + " MB"
            }

            // Buttons
            var buttonCell = document.createElement("TD")
            row.appendChild(buttonCell)

            if (files[i]["to_copy"] == 1) {
                // Loading symbol
                buttonCell.appendChild(document.createElement("DIV"))
                buttonCell.lastChild.classList.add("loading")
                buttonCell.lastChild.appendChild(document.createElement("IMG"))
                buttonCell.lastChild.firstChild.classList.add("loading")
                buttonCell.lastChild.firstChild.src = "/static/img/loading.gif"
            } else {
                // Trash can
                buttonCell.appendChild(document.createElement("BUTTON"))
                buttonCell.firstChild.innerHTML = "\u{1f5d1}"
                function deleteFunc(filename) {
                    return function () {
                        request("POST", "/delete_file", function () {
                            getFiles()
                        }, {
                            "filename": filename,
                        }, "Failed to delete file.")
                    }
                }
                buttonCell.firstChild.onclick = deleteFunc(files[i]["filename"])
                buttonCell.firstChild.classList.add("emoji")
            }

            table.appendChild(row)
        }
    }, {})
}
getFiles()
setInterval(getFiles, 2000)

// Unmount USB drive
var unmountTimeout
function unmount() {
    request("POST", "/unmount_usb", function () {
        clearTimeout(unmountTimeout)
        alert("\u{2714} Safe to remove USB drive.")
    }, {}, "Failed to unmount USB drive. DO NOT REMOVE")
    unmountTimeout = setTimeout(function () {
        alert("Ejecting the USB drive is taking longer than expected. Please wait for completion. DO NOT REMOVE")
    }, 1000)
}