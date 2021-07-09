from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

import asyncio
from uvicorn import run
from typing import Optional
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from name import new as newName
from time import time, sleep
from uuid import uuid4
import numpy as np
import json

from store import DataLoader

from config import *


s = DataLoader()

    
app = FastAPI()
templates = Jinja2Templates(directory="templates")

types = ["HYBRID", "CPU", "GPU"]


# REQUEST INPUTS START ------


class TokenInput(BaseModel):
    token: str
    type: Optional[str] = "HYBRID"

class TokenProgressInput(BaseModel):
    token: str
    progress: str
    type: Optional[str] = "HYBRID"

class TokenCountInput(BaseModel): # For marking as done
    token: str
    type: Optional[str] = "HYBRID"
        
    count: Optional[int] = None  # `count` is for HYBRID/GPU
    
    url: Optional[str] = None    # CPU vvv
    start_id: Optional[str] = None
    end_id: Optional[str] = None
    shard: Optional[int] = None

class BanShardCountInput(BaseModel):
    password: str
    count: int

class LookupWatInput(BaseModel):
    password: str
    url: str

class MarkAsDoneInput(BaseModel):
    password: str
    shards: list
    count: int
    nickname: str
        

# FRONTEND START ------


@app.get('/', response_class=HTMLResponse)
async def index(request: Request, all: Optional[bool] = False):
    return templates.TemplateResponse('index.html', {"request": request, "all": all, "clients": s.clients, "completion": s.completion, "progress_str": s.progress_str, "total_pairs": s.total_pairs, "eta": s.eta})


@app.get('/install', response_class=HTMLResponse)
async def install(request: Request):
    return templates.TemplateResponse('install.html', {"request": request})


@app.get('/leaderboard', response_class=HTMLResponse)
async def leaderboard_page(request: Request):
    return templates.TemplateResponse('leaderboard.html', {"request": request, "leaderboard": dict(sorted(s.leaderboard.items(), key=lambda x: x[1], reverse=True))})


@app.get('/worker/{type}/{worker}', response_class=HTMLResponse)
async def worker_info(type: str, worker: str, request: Request):
    type = type.upper()
    if type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    if worker in s.worker_cache[type]:
        w = s.clients[type][s.worker_cache[type][worker]]
    else:
        w = None
        for token in s.clients[type]:
            if s.clients[type][token]["display_name"] == worker:
                w = s.clients[type][token]
                s.worker_cache[type][worker] = token
                if len(s.worker_cache[type]) > MAX_WORKER_CACHE_SIZE:
                    s.worker_cache[type].pop(0)
                break
    if not w:
        raise HTTPException(status_code=500, detail="Worker not found.")
    else:
        return templates.TemplateResponse('worker.html', {"request": request, **w})


@app.get('/data')
async def data():
    return {
        "completion_str": s.progress_str,
        "completion_float": s.completion,
        "total_connected_workers": len(s.clients["CPU"]) + len(s.clients["GPU"]) + len(s.clients["HYBRID"]),
        "total_pairs_scraped": s.total_pairs,
        "open_jobs": len(s.open_jobs),
        "pending_jobs": len(s.pending_jobs),
        "closed_jobs": len(s.closed_jobs),
        "leaderboard": s.leaderboard,
        "eta": s.eta
    }


@app.get('/worker/{type}/{worker}/data')
async def worker_data(type: str, worker: str):
    type = type.upper()
    if type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    if worker in s.worker_cache[type]:
        return s.clients[type][s.worker_cache[type][worker]]
    
    w = None
    for token in s.clients[type]:
        if s.clients[type][token]["display_name"] == worker:
            w = s.clients[type][token]
            s.worker_cache[type][worker] = token
            if len(s.worker_cache[type]) > MAX_WORKER_CACHE_SIZE:
                s.worker_cache[type].pop(0)
            break
    if not w:
        raise HTTPException(status_code=500, detail="Worker not found.")
    else:
        return w
            
        
# ADMIN START ------


@app.post('/admin/ban-shard')
async def ban_shard(inp: BanShardCountInput, request: Request):
    return {"status": "failed", "detail": "obsolete endpoint"}
#     if inp.password == ADMIN_PASSWORD:
#         user_count = inp.count
#         count = None
#         index = None
#         for i, shard in enumerate(s.open_jobs):
#             count = (np.int64(shard["end_id"]) / 1000000) * 2
#             if shard["shard"] == 0:
#                 count -= 1
            
#             if int(count) == user_count:
#                 index = i
#                 try:
#                     s.pending_jobs.remove(str(count))
#                 except:
#                     pass
#                 try:
#                     s.closed_jobs.remove(str(count))
#                 except:
#                     pass
#                 break
                
#                 s.jobs_remaining = str(len(s.open_jobs) - (len(s.pending_jobs) + len(s.closed_jobs) + len(s.open_gpu)))

#                 s.completion = (len(s.closed_jobs) / s.total_jobs) * 100
#                 s.progress_str = f"{len(s.closed_jobs):,} / {s.total_jobs:,}"
        
        
#         if index is None:
#             return {"status": "failed", "detail": "Could not find that shard."}
#         else:
#             del s.open_jobs[index]
        
#         return {"status": "success"}
#     else:
#         return {"status": "failed", "detail": "You are not an admin!"}


@app.post('/admin/reset-shard')
async def reset_shard(inp: BanShardCountInput, request: Request):
    if inp.password == ADMIN_PASSWORD:
        user_count = inp.count
        
        try:
            s.closed_jobs.remove(str(user_count))
        except ValueError:
            return {"status": "failed", "detail": "Shard not found!"}
                
        s.jobs_remaining = str(len(s.open_jobs) - (len(s.pending_jobs) + len(s.closed_jobs) + len(s.open_gpu)))

        s.completion = (len(s.closed_jobs) / s.total_jobs) * 100
        s.progress_str = f"{len(s.closed_jobs):,} / {s.total_jobs:,}"
         
        
        return {"status": "success"}
    else:
        return {"status": "failed", "detail": "You are not an admin!"}
    
    
@app.post('/custom/lookup-wat')
async def lookup_wat(inp: LookupWatInput):
    if inp.password != ADMIN_PASSWORD:
        return {"status": "failed", "detail": "Invalid password."}
    
    shards = []
    for shard in s.open_jobs:
        if s.shard_info["directory"] + shard["url"] == inp.url:
            count = (np.int64(shard["end_id"]) / 1000000) * 2
            if shard["shard"] == 0:
                count -= 1
            shards.append([int(count), shard])
    
    if len(shards) == 0:
        return {"status": "failed", "detail": "Could not find WAT/WARC."}
    elif (str(shards[1][0]) in s.pending_jobs or str(shards[1][0]) in s.closed_jobs) or (str(shards[0][0]) in s.pending_jobs or str(shards[0][0]) in s.closed_jobs):
        return {"status": "failed", "detail": "Segment already (partially/fully) completed."}
    else:
        return {"status": "success", "shards": shards}
    
    
@app.post('/custom/markasdone')
async def custom_markasdone(inp: MarkAsDoneInput):
    if inp.password != ADMIN_PASSWORD:
        return {"status": "failed", "detail": "Invalid password."}
    
    existed = 0
    for shard in inp.shards:
        if str(shard) in s.closed_jobs or str(shard) in s.pending_jobs:
            continue
        else:
            for sd in s.open_jobs:
                count = (np.int64(sd["end_id"]) / 1000000) * 2
                if sd["shard"] == 0:
                    count -= 1
                if int(count) == shard:
                    s.open_jobs.remove(sd)
                    break
            s.closed_jobs.append(str(shard))
            existed += 1
    
    if existed > 0:
        try:
            s.leaderboard[inp.nickname][0] += existed
            s.leaderboard[inp.nickname][1] += inp.count
        except KeyError:
            s.leaderboard[inp.nickname] = [existed, inp.count]

        s.total_pairs += inp.count

        s.jobs_remaining = str(len(s.open_jobs) - (len(s.pending_jobs) + len(s.closed_jobs) + len(s.open_gpu)))

        s.completion = (len(s.closed_jobs) / s.total_jobs) * 100
        s.progress_str = f"{len(s.closed_jobs):,} / {s.total_jobs:,}"
        
        return {"status": "success"}
    else:
        return {"status": "failed", "detail": "Another worker has already finished this job."}
            
    
# API START ------


@app.get('/api/new')
async def new(nickname: str, type: Optional[str] = "HYBRID"):
    if type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    if s.jobs_remaining == "0" and type != "GPU":
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
        "display_name": display_name,
        "type": type
    }

    s.clients[type][uuid] = worker_data

    return {"display_name": display_name, "token": uuid}


@app.post('/api/validateWorker', response_class=PlainTextResponse)
async def validateWorker(inp: TokenInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    return str(inp.token in s.clients[inp.type])


@app.post('/api/newJob')
async def newJob(inp: TokenInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    token = inp.token
    if token not in s.clients[inp.type]:
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?\n\nYou could also have an out of date client. Check the footer of the home page for the latest version numbers.")

    if s.jobs_remaining == "0":
        raise HTTPException(status_code=503, detail="No new jobs available.")
    
    if inp.type == "GPU":
        for i in s.open_gpu:
            if i[0] in s.pending_gpu:
                continue
            else:
                s.pending_gpu.append(i[0])
                
                s.clients[inp.type][token]["shard_number"] = int(i[0])
                s.clients[inp.type][token]["progress"] = "Recieved new job"
                s.clients[inp.type][token]["last_seen"] = time()
                
                return i[1]
            
        raise HTTPException(status_code=503, detail="No new GPU jobs available. Keep retrying, as GPU jobs are dynamically created.")
    else:
        if s.clients[inp.type][token]["shard_number"] != "Waiting":
            try:
                s.pending_jobs.remove(str(s.clients[token]["shard_number"]))
            except ValueError:
                pass

        c = 0
        shard = s.open_jobs[c]

        count = (np.int64(shard["end_id"]) / 1000000) * 2
        if shard["shard"] == 0:
            count -= 1

        count = int(count)

        while str(count) in s.pending_jobs or str(count) in s.closed_jobs or str(count) in [i[0] for i in s.open_gpu]:
            c += 1
            shard = s.open_jobs[c]

            count = (np.int64(shard["end_id"]) / 1000000) * 2
            if shard["shard"] == 0:
                count -= 1

            count = int(count)

        s.pending_jobs.append(str(count))
        s.jobs_remaining = str(len(s.open_jobs) - (len(s.pending_jobs) + len(s.closed_jobs) + len(s.open_gpu)))

        s.clients[inp.type][token]["shard_number"] = count
        s.clients[inp.type][token]["progress"] = "Recieved new job"
        s.clients[inp.type][token]["last_seen"] = time()

        return {"url": s.shard_info["directory"] + shard["url"], "start_id": shard["start_id"], "end_id": shard["end_id"], "shard": shard["shard"]}


@app.get('/api/jobCount', response_class=PlainTextResponse)
async def jobCount(type: Optional[str] = "HYBRID"):
    if type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
        
    if type == "GPU":
        return str(len(s.open_gpu) - len(s.pending_gpu))
    else:
        return str(s.jobs_remaining)


@app.post('/api/updateProgress', response_class=PlainTextResponse)
async def updateProgress(inp: TokenProgressInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    token = inp.token
    if token not in s.clients[inp.type]:
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?\n\nYou could also have an out of date client. Check the footer of the home page for the latest version numbers.")

    s.clients[inp.type][token]["progress"] = inp.progress
    s.clients[inp.type][token]["last_seen"] = time()
    
    return "success"


@app.post('/api/markAsDone', response_class=PlainTextResponse)
async def markAsDone(inp: TokenCountInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    token = inp.token
    if token not in s.clients[inp.type]:
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?\n\nYou could also have an out of date client. Check the footer of the home page for the latest version numbers.")

    if inp.type == "CPU":
        if inp.url is None or inp.start_id is None or inp.end_id is None or inp.shard is None:
            raise HTTPException(status_code=500, detail="The worker did not submit valid input data.")
        if s.clients[inp.type][token]["shard_number"] == "Waiting":
            raise HTTPException(status_code=500, detail="You do not have an open job.")
            
        s.open_gpu.append([
            str(s.clients[inp.type][token]["shard_number"]),
            {
                "url": inp.url,
                "start_id": inp.start_id,
                "end_id": inp.end_id,
                "shard": inp.shard
            }
        ])
        
        s.clients[inp.type][token]["shard_number"] = "Waiting"
        s.clients[inp.type][token]["progress"] = "Completed Job"
        s.clients[inp.type][token]["jobs_completed"] += 1
        s.clients[inp.type][token]["last_seen"] = time()
        
        return "success"
    else:
        if not inp.count:
            raise HTTPException(status_code=500, detail="The worker did not submit a valid count!")
            
        if str(s.clients[inp.type][token]["shard_number"]) in s.closed_jobs:
            return "job already completed, not raising error"
        
        if inp.type == "GPU":
            for i in s.open_gpu:
                if i[0] == str(s.clients[inp.type][token]["shard_number"]):
                    s.open_gpu.remove(i)
                    break
            
            s.pending_gpu.remove(str(s.clients[inp.type][token]["shard_number"]))
        else:
            try:
                s.pending_jobs.remove(str(s.clients[inp.type][token]["shard_number"]))
            except ValueError:
                raise HTTPException(status_code=500, detail="This job has already been marked as completed!")
             
        s.closed_jobs.append(str(s.clients[inp.type][token]["shard_number"]))
        
        for shard in s.open_jobs:
            count = (np.int64(shard["end_id"]) / 1000000) * 2
            if shard["shard"] == 0:
                count -= 1
            if int(count) == s.clients[inp.type][token]["shard_number"]:
                s.open_jobs.remove(shard)
                break
                
        s.jobs_remaining = str(len(s.open_jobs) - (len(s.pending_jobs) + len(s.closed_jobs) + len(s.open_gpu)))

        s.completion = (len(s.closed_jobs) / s.total_jobs) * 100
        s.progress_str = f"{len(s.closed_jobs):,} / {s.total_jobs:,}"

        s.clients[inp.type][token]["shard_number"] = "Waiting"
        s.clients[inp.type][token]["progress"] = "Completed Job"
        s.clients[inp.type][token]["jobs_completed"] += 1
        s.clients[inp.type][token]["last_seen"] = time()

        try:
            s.leaderboard[s.clients[inp.type][token]["user_nickname"]][0] += 1
            s.leaderboard[s.clients[inp.type][token]["user_nickname"]][1] += inp.count
        except KeyError:
            s.leaderboard[s.clients[inp.type][token]["user_nickname"]] = [1, inp.count]
            
    s.total_pairs += inp.count

    return "success"


@app.post('/api/gpuInvalidDownload', response_class=PlainTextResponse)
async def gpuInvalidDownload(inp: TokenInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    token = inp.token
    if token not in s.clients[inp.type]:
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?\n\nYou could also have an out of date client. Check the footer of the home page for the latest version numbers.")
    
    for i in s.open_gpu:
        if i[0] == str(s.clients[inp.type][token]["shard_number"]):
            s.open_gpu.remove(i)
            break
    
    try:
        s.pending_gpu.remove(str(s.clients[inp.type][token]["shard_number"]))
    except ValueError:
        pass
    
    return "success"

    
@app.post('/api/bye', response_class=PlainTextResponse)
async def bye(inp: TokenInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    token = inp.token
    if token not in s.clients[inp.type]:
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?\n\nYou could also have an out of date client. Check the footer of the home page for the latest version numbers.")

    try:
        if inp.type == "GPU":
            s.pending_gpu.remove(str(s.clients[inp.type][token]["shard_number"]))
        else:
            s.pending_jobs.remove(str(s.clients[inp.type][token]["shard_number"]))
    except ValueError:
        pass

    del s.clients[inp.type][token]
    
    if token in s.worker_cache[inp.type]:
        del s.worker_cache[inp.type][token]
    
    return "success"


# TIMERS START ------


async def check_idle(timeout):
    while True:
        for type in types:
            for client in list(s.clients[type].keys()):
                if (time() - s.clients[type][client]["last_seen"]) > timeout:
                    try:
                        if type == "GPU":
                            s.pending_gpu.remove(str(s.clients[type][client]["shard_number"]))
                        else:
                            s.pending_jobs.remove(str(s.clients[type][client]["shard_number"]))
                    except:
                        pass
                    
                    if client in s.worker_cache[type]:
                        del s.worker_cache[type][client]

                    del s.clients[type][client]

        await asyncio.sleep(30)

        
async def calculate_eta():
    def _format_time(s):
        s = int(s)
        y, s = divmod(s, 31_536_000)
        d, s = divmod(s, 86400)
        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)
        if y:
            return f"{y} year{'s' if y!=1 else ''}, {d} day{'s' if d!=1 else ''}, {h} hour{'s' if h!=1 else ''}, {m} minute{'s' if m!=1 else ''} and {s} second{'s' if s!=1 else ''}"
        elif d:
            return f"{d} day{'s' if d!=1 else ''}, {h} hour{'s' if h!=1 else ''}, {m} minute{'s' if m!=1 else ''} and {s} second{'s' if s>1 else ''}"
        elif h:
            return f"{h} hour{'s' if h!=1 else ''}, {m} minute{'s' if m!=1 else ''} and {s} second{'s' if s>1 else ''}"
        elif m:
            return f"{m} minute{'s' if m!=1 else ''} and {s} second{'s' if s!=1 else ''}"
        else:
            return f"{s} second{'s' if s!=1 else ''}"

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
        
        if length:
            s.eta = _format_time(length)
        else:
            s.eta = "Finished"

        
async def save_jobs_leaderboard():
    a = len(s.closed_jobs)
    b = sum([s.leaderboard[i][1] for i in s.leaderboard])
    c = len(s.open_gpu)
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
        z = len(s.open_gpu)
        if c != z:
            with open("jobs/open_gpu.json", "w") as f:
                json.dump(s.open_gpu, f)

        a = x
        b = y
        c = z
        

# FASTAPI UTILITIES START ------ 
    
    
@app.on_event('startup')
async def app_startup():
    if __name__ == "__main__":
        asyncio.create_task(check_idle(IDLE_TIMEOUT))
        asyncio.create_task(calculate_eta())
        asyncio.create_task(save_jobs_leaderboard())

  
@app.on_event('shutdown')
async def shutdown_event():
    if __name__ == "__main__":
        with open("jobs/closed.json", "w") as f:
            json.dump(s.closed_jobs, f)

        with open("jobs/leaderboard.json", "w") as f:
            json.dump(s.leaderboard, f)
        
        with open("jobs/open_gpu.json", "w") as f:
            json.dump(s.open_gpu, f)

        
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


# ------------------------------ 


if __name__ == "__main__":
    run(app, host=HOST, port=PORT) #, workers=WORKERS_COUNT [multiprocessing was reverted for v2.1.0, will be added at a later date TBD]
