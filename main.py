from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import asyncio
from uvicorn import run
from typing import Optional
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from name import new as newName
from datetime import timedelta
from time import time, sleep
from threading import Thread
from uuid import uuid4
from copy import copy
import numpy as np
import json

from store import DataLoader

from config import (
    HOST, PORT, WORKERS_COUNT,
    IDLE_TIMEOUT,
    AVERAGE_INTERVAL, AVERAGE_DATASET_LENGTH,
    ADMIN_IPS
)


s = DataLoader()


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


raw_text_stats = "<strong>Completion:</strong> {} ({}%)<br><strong>Connected Workers:</strong> {}<br><strong>Alt-Text Pairs Scraped:</strong> {}<br><br><strong>Job Info</strong><br>Open Jobs: {}<br>Current Jobs: {}<br>Closed Jobs: {}<br><br><br><i>This page should be used when there are many workers connected to the server to prevent slow loading times.</i>"    


# REQUEST INPUTS START ------

class TokenInput(BaseModel):
    token: str

class TokenProgressInput(BaseModel):
    token: str
    progress: str

class TokenCountInput(BaseModel):
    token: str
    count: int

class BanShardCountInput(BaseModel):
    count: int
        

# FRONTEND START ------


@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse('index.html', {"request": request, "len": len, "clients": s.clients, "completion": s.completion, "progress_str": s.progress_str, "total_pairs": s.total_pairs, "eta": s.eta})


@app.get('/install', response_class=HTMLResponse)
async def install(request: Request):
    return templates.TemplateResponse('install.html', {"request": request})


@app.get('/leaderboard', response_class=HTMLResponse)
async def leaderboard_page(request: Request):
    return templates.TemplateResponse('leaderboard.html', {"request": request, "len": len, "leaderboard": dict(sorted(s.leaderboard.items(), key=lambda x: x[1], reverse=True))})


@app.get('/stats', response_class=HTMLResponse)
async def stats():
    return raw_text_stats.format(progress_str, s.completion, len(s.clients), s.total_pairs, len(s.open_jobs), len(s.pending_jobs), len(s.closed_jobs))


@app.get('/workers/{worker}', response_class=HTMLResponse)
async def worker_info(worker: str):
    w = None
    for token in c.clients:
        if c.clients[token]["display_name"] == worker:
            w = copy(c.clients[token])
            break
            
    if not w:
        raise HTTPException(status_code=500, detail="Worker not found.")
    else:
        return return templates.TemplateResponse('worker.html', {"request": request, **w})
    


@app.get('/data')
async def data():
    return {
        "completion_str": s.progress_str,
        "completion_float": s.completion,
        "total_connected_workers": len(s.clients),
        "total_pairs_scraped": s.total_pairs,
        "open_jobs": len(s.open_jobs),
        "pending_jobs": len(s.pending_jobs),
        "closed_jobs": len(s.closed_jobs),
        "leaderboard": s.leaderboard,
        "eta": s.eta
    }


@app.get('/workers/{worker}/data')
async def worker_data(worker: str):
    w = None
    for token in c.clients:
        if c.clients[token]["display_name"] == worker:
            w = copy(c.clients[token])
            break
            
    if not w:
        raise HTTPException(status_code=500, detail="Worker not found.")
    else:
        return w
            
        
# ADMIN START ------

@app.post('/admin/ban-shard')
async def data(inp: BanShardCountInput, request: Request):
    if request.client.host in ADMIN_IPS:
        user_count = inp.count
        count = None
        index = None
        for i, shard in enumerate(s.open_jobs):
            count = (np.int64(shard["end_id"]) / 1000000) * 2
            if shard["shard"] == 0:
                count -= 1
            
            if int(count) == user_count:
                index = i
                try:
                    s.pending_jobs.remove(str(count))
                except:
                    pass
                try:
                    s.closed_jobs.remove(str(count))
                except:
                    pass
                break
         
        del s.open_jobs[index]
        
        with open("jobs/open.json", "w") as f:
            json.dump(s.open_jobs, f)
        with open("jobs/closed.json", "w") as f:
            json.dump(s.closed_jobs, f)
        
        return {"status": "success"}
    else:
        return {"status": "failed", "detail": "You are not an admin!"}
    
    
# API START ------


@app.get('/api/new')
async def new(nickname: str):
    if len(s.open_jobs) == 0 or len(s.open_jobs) == len(s.pending_jobs):
        raise HTTPException(status_code=503, detail="No new jobs available.")
    
    display_name = newName()
    uuid = str(uuid4())
    ctime = time()
    
    worker_data = {
        "shard_number": "Waiting",
        "progress": "Initialized",
        "jobs_completed": 0,
        "first_seen": ctime,
        "last_seen": ctime,
        "user_nickname": nickname,
        "display_name": display_name
    }

    s.clients[uuid] = worker_data

    return {"display_name": display_name, "token": uuid}


@app.post('/api/newJob')
async def newJob(inp: Optional[TokenInput] = None):
    if not inp:
        raise HTTPException(status_code=500, detail="You appear to be using an old client. Please check the Crawling@Home website (http://crawlingathome.duckdns.org/) for the latest version numbers.")
    token = inp.token
    if token not in s.clients:
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?\n\nYou could also have an out of date client. Check the footer of the home page for the latest version numbers.")

    if len(s.open_jobs) == 0 or len(s.open_jobs) == len(s.pending_jobs):
        raise HTTPException(status_code=503, detail="No new jobs available.")
    
    if s.clients[token]["shard_number"] != "Waiting":
        try:
            s.pending_jobs.remove(str(s.clients[token]["shard_number"]))
        except:
            pass

    c = 0
    shard = s.open_jobs[c]
    
    count = (np.int64(shard["end_id"]) / 1000000) * 2
    if shard["shard"] == 0:
        count -= 1
    
    count = count.astype(int)
    
    while str(count) in s.pending_jobs or str(count) in s.closed_jobs:
        c += 1
        shard = s.open_jobs[c]
        
        count = (np.int64(shard["end_id"]) / 1000000) * 2
        if shard["shard"] == 0:
            count -= 1
        
        count = count.astype(int)
    
    s.pending_jobs.append(str(int))

    s.clients[token]["shard_number"] = count
    s.clients[token]["progress"] = "Recieved new job"
    s.clients[token]["last_seen"] = time()

    return {"url": s.shard_info["directory"] + shard["url"], "start_id": shard["start_id"], "end_id": shard["end_id"], "shard": shard["shard"]}


@app.get('/api/jobCount', response_class=PlainTextResponse)
async def jobCount():
    return str(len(s.open_jobs) - (len(s.pending_jobs) + len(s.closed_jobs)))


@app.post('/api/updateProgress', response_class=PlainTextResponse)
async def updateProgress(inp: Optional[TokenProgressInput] = None):
    if not inp:
        raise HTTPException(status_code=500, detail="You appear to be using an old client. Please check the Crawling@Home website (http://crawlingathome.duckdns.org/) for the latest version numbers.")
    token = inp.token
    if token not in s.clients:
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?\n\nYou could also have an out of date client. Check the footer of the home page for the latest version numbers.")

    s.clients[token]["progress"] = inp.progress
    s.clients[token]["last_seen"] = time()
    
    return "success"


@app.post('/api/markAsDone', response_class=PlainTextResponse)
async def markAsDone(inp: Optional[TokenCountInput] = None):
    if not inp:
        raise HTTPException(status_code=500, detail="You appear to be using an old client. Please check the Crawling@Home website (http://crawlingathome.duckdns.org/) for the latest version numbers.")
    token = inp.token
    if token not in s.clients:
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?\n\nYou could also have an out of date client. Check the footer of the home page for the latest version numbers.")

        
    s.pending_jobs.remove(str(s.clients[token]["shard_number"]))
    s.closed_jobs.append(str(s.clients[token]["shard_number"])) # !! NEWER SERVERS SHOULD PROBABLY STORE THE DATA INSTEAD OF THE NUMBER !!
    
    s.completion = (len(s.closed_jobs) / s.total_jobs) * 100
    s.progress_str = f"{len(s.closed_jobs):,} / {s.total_jobs:,}"

    s.clients[token]["shard_number"] = "Waiting"
    s.clients[token]["progress"] = "Completed Job"
    s.clients[token]["jobs_completed"] += 1
    s.clients[token]["last_seen"] = time()

    try:
        s.leaderboard[s.clients[token]["user_nickname"]][0] += 1
        s.leaderboard[s.clients[token]["user_nickname"]][1] += inp.count
    except:
        s.leaderboard[s.clients[token]["user_nickname"]] = [1, inp.count]
    
    s.total_pairs += inp.count
     
    return "success"


@app.post('/api/bye', response_class=PlainTextResponse)
async def bye(inp: Optional[TokenInput] = None):
    if not inp:
        raise HTTPException(status_code=500, detail="You appear to be using an old client. Please check the Crawling@Home website (http://crawlingathome.duckdns.org/) for the latest version numbers.")
    token = inp.token
    if token not in s.clients:
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?\n\nYou could also have an out of date client. Check the footer of the home page for the latest version numbers.")

    try:
        s.pending_jobs.remove(str(s.clients[token]["shard_number"]))
    except:
        pass

    del s.clients[token]
    
    return "success"


# TIMERS START ------


async def check_idle(timeout):
    while True:
        for client in list(s.clients.keys()):
            if (time() - s.clients[client]["last_seen"]) > timeout:
                try:
                    s.pending_jobs.remove(str(s.clients[client]["shard_number"]))
                except:
                    pass

                del s.clients[client]

        await asyncio.sleep(30)

        
async def calculate_eta():
    dataset = []
    while True:
        start = len(s.closed_jobs)
        await asyncio.sleep(AVERAGE_INTERVAL)
        end = len(s.closed_jobs)

        dataset.append(end - start)
        if len(dataset) > AVERAGE_DATASET_LENGTH:
            dataset.pop(0)

        mean = sum(dataset) / len(dataset)
        mean_per_second = mean / AVERAGE_INTERVAL
        remaining = len(s.open_jobs) - len(s.pending_jobs)

        try:
            length = remaining // mean_per_second
        except ZeroDivisionError:
            continue

        s.eta = str(timedelta(seconds=length))

        
async def save_jobs_leaderboard():
    a = len(s.closed_jobs)
    b = sum([s.leaderboard[i][1] for i in s.leaderboard])
    while True:
        await asyncio.sleep(300)

        x = len(s.closed_jobs)
        if a != x:
            with open("jobs/closed.json", "w") as f:
                json.dump(s.closed_jobs, f)
        y = sum([s.leaderboard[i][1] for i in s.leaderboard])
        if b != y:
            with open("jobs/leaderboard.json", "w") as f:
                json.dump(s.leaderboard, f)

        a = x
        b = y
        

# FASTAPI UTILITIES START ------ 
    
    
@app.on_event('startup')
async def app_startup():
    asyncio.create_task(check_idle(IDLE_TIMEOUT))
    asyncio.create_task(calculate_eta())
    asyncio.create_task(save_jobs_leaderboard())

  
@app.on_event('shutdown')
async def shutdown_event():
    with open("jobs/closed.json", "w") as f:
        json.dump(s.closed_jobs, f)
        
    with open("jobs/leaderboard.json", "w") as f:
        json.dump(s.leaderboard, f)

        
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)
    
    
# ------------------------------ 
    
    
if __name__ == "__main__":
    run(app, host=HOST, port=PORT) # ,workers=WORKERS_COUNT
