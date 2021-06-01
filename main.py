from flask import Flask, render_template, request, jsonify
from name import new as newName
from datetime import timedelta
from time import time, sleep
from threading import Thread
from copy import deepcopy
from uuid import uuid4
import numpy as np
import json

from config import HOST, PORT, IDLE_TIMEOUT, AVERAGE_INTERVAL, AVERAGE_DATASET_LENGTH


web_site = Flask(__name__)


clients = {}


with open("jobs/shard_info.json", "r") as f:
    shard_info = json.load(f)

with open("jobs/open.json", "r") as f:
    open_jobs = json.load(f)

with open("jobs/closed.json", "r") as f:
    closed_jobs = json.load(f)

with open("jobs/leaderboard.json", "r") as f:
    leaderboard = json.load(f)

pending_jobs = []

total_jobs = shard_info["total_shards"]

total_pairs = sum([leaderboard[i][1] for i in leaderboard])


try:
    completion = (len(closed_jobs) / total_jobs) * 100
    progress_str = f"{len(closed_jobs)} / {total_jobs}"
except ZeroDivisionError:
    completion = 0.00
    progress_str = "0 / 0"


eta = "N/A"


raw_text_stats = "<strong>Completion:</strong> {} ({}%)<br><strong>Connected Workers:</strong> {}<br><strong>Alt-Text Pairs Scraped:</strong> {}<br><br><strong>Job Info</strong><br>Open Jobs: {}<br>Current Jobs: {}<br>Closed Jobs: {}<br><br><br><i>This page should be used when there are many workers connected to the server to prevent slow loading times.</i>"    


# FRONTEND START ------


@web_site.route('/')
def index():
    return render_template('index.html', len=len, clients=clients, completion=completion, progress_str=progress_str, total_pairs=total_pairs, eta=eta)

@web_site.route('/install')
def install():
    return render_template('install.html')

@web_site.route('/leaderboard')
def leaderboard_page():
    return render_template('leaderboard.html', len=len, leaderboard=dict(sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)))

@web_site.route('/stats')
def stats():
    return raw_text_stats.format(progress_str, completion, len(clients), total_pairs, len(open_jobs), len(pending_jobs), len(closed_jobs))

@web_site.route('/data')
def data():
    return jsonify({
        "completion_str": progress_str,
        "completion_float": completion,
        "total_connected_workers": len(clients),
        "total_pairs_scraped": total_pairs,
        "open_jobs": len(open_jobs),
        "pending_jobs": len(pending_jobs),
        "closed_jobs": len(closed_jobs)
    })

# API START ------


@web_site.route('/api/new', methods=["GET"])
def new():
    global clients, open_jobs, pending_jobs

    if len(open_jobs) == 0 or len(open_jobs) == len(pending_jobs):
        return "No new jobs available.", 503
    
    display_name = newName()
    uuid = str(uuid4())
    
    worker_data = {
        "shard_number": "Waiting",
        "progress": "Initialized",
        "jobs_completed": 0,
        "last_seen": time(),
        "shard_data": None,
        "user_nickname": request.args["nickname"],
        "display_name": display_name
    }

    clients[uuid] = worker_data

    return jsonify({"display_name": display_name, "token": uuid})


@web_site.route('/api/newJob', methods=["POST"])
def newJob():
    global clients, pending_jobs, open_jobs

    token = request.json["token"]
    if token not in clients:
        return "The server could not find this worker. Did the server just restart?\n\nYou could also have an out of date client. Check the footer of the home page for the latest version numbers.", 500

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

    clients[token]["shard_number"] = str(int(count))
    clients[token]["progress"] = "Recieved new job"
    clients[token]["last_seen"] = time()
    clients[token]["shard_data"] = shard

    return jsonify({"url": shard_info["directory"] + shard["url"], "start_id": shard["start_id"], "end_id": shard["end_id"], "shard": shard["shard"]})


@web_site.route('/api/jobCount', methods=["GET"])
def jobCount():
    global open_jobs, pending_jobs

    return str(len(open_jobs) - len(pending_jobs))


@web_site.route('/api/updateProgress', methods=["POST"])
def updateProgress():
    global clients
    
    token = request.json["token"]
    if token not in clients:
        return "The server could not find this worker. Did the server just restart?\n\nYou could also have an out of date client. Check the footer of the home page for the latest version numbers.", 500

    clients[token]["progress"] = request.json["progress"]
    clients[token]["last_seen"] = time()


@web_site.route('/api/bye', methods=["POST"])
def bye():
    global clients, pending_jobs
    
    token = request.json["token"]
    if token not in clients:
        return "The server could not find this worker. Did the server just restart?\n\nYou could also have an out of date client. Check the footer of the home page for the latest version numbers.", 500

    try:
        pending_jobs.remove(clients[token]["shard_data"])
    except:
        pass

    del clients[token]


@web_site.route('/api/markAsDone', methods=["POST"])
def markAsDone():
    global clients, open_jobs, pending_jobs, closed_jobs, completion, progress_str, leaderboard, total_pairs

    token = request.json["token"]
    if token not in clients:
        return "The server could not find this worker. Did the server just restart?\n\nYou could also have an out of date client. Check the footer of the home page for the latest version numbers.", 500
    
    count = request.json["count"]

    
    open_jobs.remove(clients[token]["shard_data"])
    pending_jobs.remove(clients[token]["shard_data"])
    closed_jobs.append(clients[token]["shard_number"]) # !! NEWER SERVERS SHOULD PROBABLY STORE THE DATA INSTEAD OF THE NUMBER !!

    with open("jobs/open.json", "w") as f:
        json.dump(open_jobs, f)
    with open("jobs/closed.json", "w") as f:
        json.dump(closed_jobs, f)
    
    completion = (len(closed_jobs) / total_jobs) * 100
    progress_str = f"{len(closed_jobs)} / {total_jobs}"

    clients[token]["progress"] = "Completed Job"
    clients[token]["jobs_completed"] += 1
    clients[token]["last_seen"] = time()

    try:
        leaderboard[clients[token]["user_nickname"]][0] += 1
        leaderboard[clients[token]["user_nickname"]][1] += count
    except:
        leaderboard[clients[token]["user_nickname"]] = [1, count]
    
    total_pairs += count

    with open("jobs/leaderboard.json", "w") as f:
        json.dump(leaderboard, f)


def check_idle(timeout):
    global clients, pending_jobs

    while True:
        for client in list(clients.keys()):
            if (time() - clients[client]["last_seen"]) > timeout:
                try:
                    pending_jobs.remove(clients[client]["shard_data"])
                except:
                    pass
                
                del clients[client]

        sleep(30)

def calculate_eta():
    global eta, closed_jobs, open_jobs, pending_jobs
    
    dataset = []
    while True:
        start = len(closed_jobs)
        sleep(AVERAGE_INTERVAL)
        end = len(closed_jobs)
        
        dataset.append(end - start)
        if len(dataset) > AVERAGE_DATASET_LENGTH:
            dataset.pop(0)
        
        mean = sum(dataset) / len(dataset)
        mean_per_second = mean / AVERAGE_INTERVAL
        remaining = len(open_jobs) - len(pending_jobs)
        
        try:
            length = remaining // mean_per_second
        except ZeroDivisionError:
            continue
        
        eta = str(timedelta(seconds=length))
    

    
Thread(target=check_idle, args=(IDLE_TIMEOUT,)).start()
Thread(target=calculate_eta).start()

web_site.run(host=HOST, port=PORT)
