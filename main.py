from flask import Flask, render_template, request, send_file, jsonify
from name import new as newName
from time import time, sleep
from threading import Thread
import numpy as np
import json

from config import HOST, PORT, IDLE_TIMEOUT

with open("jobs/shard_info.json", "r") as f:
    shard_info = json.load(f)

web_site = Flask(__name__)

clients = {}
# { "uuid": [current_shard : str, progress : str, jobs_completed : int, last_seen : float, shard_data : dict, owner_nickname : str], ... }

with open("jobs/open.json", "r") as f:
    open_jobs = json.load(f)

pending_jobs = []

with open("jobs/closed.json", "r") as f:
    closed_jobs = json.load(f)

with open("jobs/leaderboard.json", "r") as f:
    leaderboard = json.load(f)

total_jobs = shard_info["total_shards"]

try:
    completion = (len(closed_jobs) / total_jobs) * 100
    progress_str = f"{len(closed_jobs)} / {total_jobs}"
except ZeroDivisionError:
    completion = 0.00
    progress_str = "0 / 0"
    
raw_text_stats = "<strong>Completion:</strong> {} ({}%)<br><strong>Connected Nodes:</strong> {}<br><br><strong>Job Info</strong><br>Open Jobs: {}<br>Current Jobs: {}<br>Closed Jobs: {}<br><br><br><i>This page should be used when there are many nodes connected to the server to prevent slow loading times.</i>"    

@web_site.route('/')
def index():
    total_pairs = sum([int(i[1]) for i in leaderboard])
    return render_template('index.html', len=len, clients=clients, completion=completion, progress_str=progress_str, total_pairs=total_pairs)

@web_site.route('/install')
def install():
    return render_template('install.html')

@web_site.route('/leaderboard')
def leaderboard_page():
    return render_template('leaderboard.html', len=len, leaderboard=dict(sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)))

@web_site.route('/stats')
def stats():
    return raw_text_stats.format(progress_str, completion, len(clients), len(open_jobs), len(pending_jobs), len(closed_jobs))


# API START ------


@web_site.route('/api/new', methods=["GET"])
def new():
    global clients, open_jobs, pending_jobs

    if len(open_jobs) == 0 or len(open_jobs) == len(pending_jobs):
        return "No new jobs available.", 503
    
    name = newName()

    clients[name] = ["Waiting", "Initialized", 0, time(), None, request.args.get("nickname", "None")]

    return name

@web_site.route('/api/newJob', methods=["POST"])
def newJob():
    global clients, pending_jobs, open_jobs

    name = request.json["name"]

    if len(open_jobs) == 0 or len(open_jobs) == len(pending_jobs):
        return "No new jobs available.", 503

    c = 0
    shard = open_jobs[c]
    while shard in pending_jobs:
        c += 1
        shard = open_jobs[c]
    
    pending_jobs.append(shard)

    count = (np.int64(shard["end_id"]) / 1000000) * 2
    if shard["shard"] == 0:
        count -= 1

    clients[name][0] = str(int(count))
    clients[name][1] = "Recieved new job"
    clients[name][3] = time()
    clients[name][4] = shard

    return jsonify({"url": shard_info["directory"] + shard["url"], "start_id": shard["start_id"], "end_id": shard["end_id"], "shard": shard["shard"]})

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
        pending_jobs.remove(clients[name][4])
    except:
        pass

    del clients[name]

    return "thank you, bye!", 200


@web_site.route('/api/markAsDone', methods=["POST"])
def markAsDone():
    global clients, open_jobs, pending_jobs, closed_jobs, completion, progress_str, leaderboard

    name = request.json["name"]
    count = request.json["count"]

    open_jobs.remove(clients[name][4])
    pending_jobs.remove(clients[name][4])
    closed_jobs.append(clients[name][0])

    with open("jobs/open.json", "w") as f:
        json.dump(open_jobs, f)
    with open("jobs/closed.json", "w") as f:
        json.dump(closed_jobs, f)
    
    completion = (len(closed_jobs) / total_jobs) * 100
    progress_str = f"{len(closed_jobs)} / {total_jobs}"

    clients[name][1] = "Completed Job"
    clients[name][2] += 1
    clients[name][3] = time()

    try:
        leaderboard[clients[name][5]][0] += 1
        leaderboard[clients[name][5]][1] += count
    except:
        leaderboard[clients[name][5]] = [1, count]

    with open("jobs/leaderboard.json", "w") as f:
        json.dump(leaderboard, f)

    return "All good!", 200


def check_idle(timeout):
    global clients, pending_jobs

    while True:
        for client in list(clients.keys()):
            if (time() - clients[client][3]) > timeout:
                try:
                    pending_jobs.remove(clients[client][4])
                except:
                    pass
                
                del clients[client]

        sleep(30)
        

Thread(target=check_idle, args=(IDLE_TIMEOUT,)).start()

web_site.run(host=HOST, port=PORT)
