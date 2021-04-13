from flask import Flask, render_template, request, send_file, jsonify
from name import new as newName
from time import time, sleep
from threading import Thread
import json

from config import HOST, PORT

with open("jobs/shard_info.json", "r") as f:
    shard_info = json.load(f)

web_site = Flask(__name__)

clients = {}
# { "uuid": [current_shard : str, progress : str, jobs_completed : int, last_seen : float], ... }

with open("jobs/open.json", "r") as f:
    open_jobs = json.load(f)

pending_jobs = []

with open("jobs/closed.json", "r") as f:
    closed_jobs = json.load(f)

total_jobs = shard_info["total_shards"]

try:
    completion = (len(closed_jobs) / total_jobs) * 100
    progress_str = f"{len(closed_jobs)} / {total_jobs}"
except ZeroDivisionError:
    completion = 0.00
    progress_str = "0 / 0"

@web_site.route('/')
def index():
	return render_template('index.html', len=len, clients=clients, completion=completion, progress_str=progress_str)

@web_site.route('/install')
def install():
	return render_template('install.html')

@web_site.route('/clipdist.py')
def clipdist():
	return send_file("clipdist.txt")


# API START ------


@web_site.route('/api/new', methods=["GET"])
def new():
    global clients, open_jobs, pending_jobs

    if len(open_jobs) == 0 or len(open_jobs) == len(pending_jobs):
        return "No new jobs available.", 503
    
    name = newName()

    clients[name] = ["Waiting", "Initialized", 0, time()]

    return name

@web_site.route('/api/newJob', methods=["POST"])
def newJob():
    global clients, pending_jobs, open_jobs

    name = request.json["name"]

    if len(open_jobs) == 0 or len(open_jobs) == len(pending_jobs):
        return "No new jobs available.", 503

    count = 0
    shard = open_jobs[count]
    while shard in pending_jobs:
        count += 1
        shard = open_jobs[count]
    
    pending_jobs.append(shard)

    clients[name][0] = str(count + 1)
    clients[name][1] = "Recieved new job"
    clients[name][3] = time()

    return jsonify({"url": shard_info["directory"] + shard["url"], "start_id": shard["start_id"], "end_id": shard["end_id"]})

@web_site.route('/api/jobCount', methods=["GET"])
def jobCount():
    global open_jobs, pending_jobs

    return str(len(open_jobs) - len(pending_jobs))

@web_site.route('/api/updateProgress', methods=["POST"])
def updateProgress():
    global clients
    name = request.json["name"]

    clients[name][1] = request.json["progress"]
    clients[name][3] = time()

    return "all good", 200

@web_site.route('/api/bye', methods=["POST"])
def bye():
    global clients, pending_jobs
    name = request.json["name"]

    try:
        pending_jobs.pop(int(clients[name][0]) - 1)
    except:
        pass

    del clients[name]

    return "thank you, bye!", 200


@web_site.route('/api/markAsDone', methods=["POST"])
def markAsDone():
    global clients, open_jobs, pending_jobs, closed_jobs, completion, progress_str

    name = request.args["name"]

    open_jobs.pop(int(clients[name][0]) - 1)
    pending_jobs.pop(int(clients[name][0]) - 1)
    closed_jobs.append(clients[name][0])

    with open("jobs/open.json", "w") as f:
        json.dump(open_jobs, f)
    with open("jobs/closed.json", "w") as f:
        json.dump(closed_jobs, f)
    
    completion = (len(closed_jobs) / total_jobs) * 100
    progress_str = f"{len(closed_jobs)} / {total_jobs}"

    clients[name][1] = "Uploading compiled shard"
    clients[name][2] += 1
    clients[name][3] = time()

    return "All good!", 200


def check_idle():
    global clients, pending_jobs

    while True:
        for client in list(clients.keys()):
            if (time() - clients[client][3]) > 900:
                try:
                    pending_jobs.pop(int(clients[client][0]) - 1)
                except:
                    pass
                
                del clients[client]

        sleep(30)
        

Thread(target=check_idle).start()

web_site.run(host=HOST, port=PORT)
