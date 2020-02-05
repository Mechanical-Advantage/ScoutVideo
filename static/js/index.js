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
            buttonCell.firstChild.firstChild.innerHTML = "\u{1f4f9}"
            buttonCell.firstChild.appendChild(document.createElement("SPAN"))
            buttonCell.firstChild.lastChild.innerHTML = "\u{2705}"

            // Stop button and trash can
            buttonCell.appendChild(document.createElement("DIV"))
            buttonCell.lastChild.hidden = true
            buttonCell.lastChild.appendChild(document.createElement("BUTTON"))
            buttonCell.lastChild.firstChild.innerHTML = "\u{1f6d1}"
            buttonCell.lastChild.appendChild(document.createElement("BUTTON"))
            buttonCell.lastChild.lastChild.innerHTML = "\u{1f5d1}"

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