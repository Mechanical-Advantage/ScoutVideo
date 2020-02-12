function request(method, url, response, data, error) {
    console.log(data)
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

            // Event
            row.appendChild(document.createElement("TD"))
            row.firstChild.classList.add("data")
            row.firstChild.innerHTML = matches[i]["event"]

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

            table.appendChild(row)
        }
    }, {
        event: event,
        team: team
    }, "Failed to retrieve data.")
}
