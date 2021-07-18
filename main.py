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
from random import choice
from uuid import uuid4
import numpy as np
import aiofiles
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


@app.get('/worker/{type}/{token}', response_class=HTMLResponse)
async def worker_info(type: str, token: str, request: Request):
    type = type.upper()
    if type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
        
    try:
        data = await s.redis.hgetall(type + "_" + token)
    except:
        raise HTTPException(status_code=500, detail="Worker not found.")
    
    return templates.TemplateResponse('worker.html', {"request": request, **data})


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


@app.get('/worker/{type}/{token}/data')
async def worker_data(type: str, token: str):
    type = type.upper()
    if type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    
    try:
        return await s.redis.hgetall(type + "_" + token)
    else:
        raise HTTPException(status_code=500, detail="Worker not found.")
            
        
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
                
#                 s.jobs_remaining = str(len(s.open_jobs) - (len(s.pending_jobs) + len(s.open_gpu)))

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
    return {"status": "failed", "detail": "obsolete endpoint"}
#     if inp.password == ADMIN_PASSWORD:
#         user_count = inp.count
        
#         try:
#             s.closed_jobs.remove(str(user_count))
#         except ValueError:
#             return {"status": "failed", "detail": "Shard not found!"}
                
#         s.jobs_remaining = str(len(s.open_jobs) - (len(s.pending_jobs) + len(s.open_gpu)))

#         s.completion = (len(s.closed_jobs) / s.total_jobs) * 100
#         s.progress_str = f"{len(s.closed_jobs):,} / {s.total_jobs:,}"
         
        
#         return {"status": "success"}
#     else:
#         return {"status": "failed", "detail": "You are not an admin!"}
    
    
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
        return {"status": "failed", "detail": "All shards have already been completed by another worker."}
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

        await s.redis.incrby("total_pairs", amount=inp.count)

        await s.redis.incrby("jobs_remaining", amount=-existed)

        s.completion = (len(s.closed_jobs) / s.total_jobs) * 100
        s.progress_str = f"{len(s.closed_jobs):,} / {s.total_jobs:,}"
        
        return {"status": "success"}
    else:
        return {"status": "failed", "detail": "All shards have already been completed by another worker."}
            
    
# API START ------


@app.get('/api/new')
async def new(nickname: str, type: Optional[str] = "HYBRID"):
    if type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    if s.jobs_remaining == "0" and type != "GPU":
        raise HTTPException(status_code=503, detail="No new jobs available.")
    
    uuid = str(uuid4())
    ctime = time()

    worker_data = {
        "shard_number": "Waiting",
        "progress": "Initialized",
        "jobs_completed": 0,
        "first_seen": ctime,
        "last_seen": ctime,
        "user_nickname": nickname,
        "type": type
    }

    await s.redis.hmset(type + "_" + uuid, worker_data)
    await s.redis.expire(type + "_" + uuid, IDLE_TIMEOUT)

    return {"display_name": uuid, "token": uuid, "upload_address": choice(UPLOAD_URLS)}


@app.post('/api/validateWorker', response_class=PlainTextResponse)
async def validateWorker(inp: TokenInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    return str(await s.redis.exists(inp.type + "_" + inp.token) > 0)


@app.get('/api/getUploadAddress', response_class=PlainTextResponse)
async def getUploadAddress():
    return choice(UPLOAD_URLS)


@app.post('/api/newJob')
async def newJob(inp: TokenInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    if not await s.redis.exists(inp.type + "_" + inp.token):
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?")
    
    await s.redis.expire(type + "_" + uuid, IDLE_TIMEOUT) # Update timeout
    
    if s.jobs_remaining == "0":
        raise HTTPException(status_code=503, detail="No new jobs available.")
    
    if inp.type == "GPU":
        for i in s.open_gpu:
            if i[0] in s.pending_gpu:
                continue
            else:
                s.pending_gpu.append(i[0])
                
                await s.redis.hmset(
                    inp.type + "_" + inp.token,
                    {
                        "shard_number": int(i[0]),
                        "progress": "Recieved new job",
                        "last_seen": time()
                    }
                )
                
                return i[1]
            
        raise HTTPException(status_code=503, detail="No new GPU jobs available. Keep retrying, as GPU jobs are dynamically created.")
    else:
        sn = await s.redis.hget(inp.type + "_" + inp.token, "shard_number")
        
        if sn != "Waiting":
            try:
                s.pending_jobs.remove(str(sn))
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
        s.jobs_remaining = str(len(s.open_jobs) - (len(s.pending_jobs) + len(s.open_gpu)))
        
        await s.redis.hmset(
            inp.type + "_" + inp.token,
            {
                "shard_number": count,
                "progress": "Recieved new job",
                "last_seen": time()
            }
        )

        return {"url": s.shard_info["directory"] + shard["url"], "start_id": shard["start_id"], "end_id": shard["end_id"], "shard": shard["shard"]}


@app.get('/api/jobCount', response_class=PlainTextResponse)
async def jobCount(type: Optional[str] = "HYBRID"):
    if type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
        
    if type == "GPU":
        return str(len(s.open_gpu) - len(s.pending_gpu))
    else:
        return s.jobs_remaining


@app.post('/api/updateProgress', response_class=PlainTextResponse)
async def updateProgress(inp: TokenProgressInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    if not await s.redis.exists(inp.type + "_" + inp.token):
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?")
    
    await s.redis.expire(type + "_" + uuid, IDLE_TIMEOUT) # Update timeout
    
    await s.redis.hmset(
        inp.type + "_" + inp.token,
        {
            "progress": inp.progress,
            "last_seen": time()
        }
    )
    
    return "success"


@app.post('/api/markAsDone', response_class=PlainTextResponse)
async def markAsDone(inp: TokenCountInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    if not await s.redis.exists(inp.type + "_" + inp.token):
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?")
        
    await s.redis.expire(type + "_" + uuid, IDLE_TIMEOUT) # Update timeout
    
    sn = await s.redis.hget(inp.type + "_" + inp.token, "shard_number")
    
    if inp.type == "CPU":
        if inp.url is None or inp.start_id is None or inp.end_id is None or inp.shard is None:
            raise HTTPException(status_code=500, detail="The worker did not submit valid input data.")
        if s.clients[inp.type][token]["shard_number"] == "Waiting":
            raise HTTPException(status_code=500, detail="You do not have an open job.")
        
        try:
            s.pending_jobs.remove(str(sn))
        except ValueError:
            raise HTTPException(status_code=500, detail="This job has already been marked as completed!")
            
        s.open_gpu.append([
            str(sn),
            {
                "url": inp.url,
                "start_id": inp.start_id,
                "end_id": inp.end_id,
                "shard": inp.shard
            }
        ])
        
        await s.redis.hmset(
            inp.type + "_" + inp.token,
            {
                "shard_number": "Waiting",
                "progress": "Completed Job",
                "last_seen": time()
            }
        )
        
        await s.redis.hincrby(inp.type + "_" + inp.token, "jobs_completed")
        
        return "success"
    else:
        if not inp.count:
            raise HTTPException(status_code=500, detail="The worker did not submit a valid count!")
        
        if inp.type == "GPU":
            for i in s.open_gpu:
                if i[0] == str(sn):
                    s.open_gpu.remove(i)
                    break
            
            try:
                s.pending_gpu.remove(str(sn))
            except ValueError:
                raise HTTPException(status_code=500, detail="This job has already been marked as completed!")
        else:
            try:
                s.pending_jobs.remove(str(sn))
            except ValueError:
                raise HTTPException(status_code=500, detail="This job has already been marked as completed!")
             
        s.closed_jobs.append(str(sn))
        
        for shard in s.open_jobs:
            count = (np.int64(shard["end_id"]) / 1000000) * 2
            if shard["shard"] == 0:
                count -= 1
            if int(count) == sn:
                s.open_jobs.remove(shard)
                break
                
        s.jobs_remaining = str(len(s.open_jobs) - (len(s.pending_jobs) + len(s.open_gpu)))

        s.completion = (len(s.closed_jobs) / s.total_jobs) * 100
        s.progress_str = f"{len(s.closed_jobs):,} / {s.total_jobs:,}"
        
        await s.redis.hmset(
            inp.type + "_" + inp.token,
            {
                "shard_number": "Waiting",
                "progress": "Completed Job",
                "last_seen": time()
            }
        )
        
        await s.redis.hincrby(inp.type + "_" + inp.token, "jobs_completed")

        try:
            s.leaderboard[s.clients[inp.type][token]["user_nickname"]][0] += 1
            s.leaderboard[s.clients[inp.type][token]["user_nickname"]][1] += inp.count
        except KeyError:
            s.leaderboard[s.clients[inp.type][token]["user_nickname"]] = [1, inp.count]
            
        await s.redis.incrby("total_pairs", amount=inp.count)

        return "success"


@app.post('/api/gpuInvalidDownload', response_class=PlainTextResponse)
async def gpuInvalidDownload(inp: TokenInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    if not await s.redis.exists(inp.type + "_" + inp.token):
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?")
    
    await s.redis.expire(type + "_" + uuid, IDLE_TIMEOUT) # Update timeout
    sn = await s.redis.hget(inp.type + "_" + inp.token, "shard_number")
    
    for i in s.open_gpu:
        if i[0] == str(sn):
            s.open_gpu.remove(i)
            break
    
    try:
        s.pending_gpu.remove(str(sn))
    except ValueError:
        pass
    
    await s.redis.hset(inp.type + "_" + inp.token, "last_seen", time())
    
    return "success"

    
@app.post('/api/bye', response_class=PlainTextResponse)
async def bye(inp: TokenInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    if not await s.redis.exists(inp.type + "_" + inp.token):
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?")

    sn = await s.redis.hget(inp.type + "_" + inp.token, "shard_number")
        
    try:
        if sn != "Waiting":
            if inp.type == "GPU":
                s.pending_gpu.remove(str(sn))
            else:
                s.pending_jobs.remove(str(sn))
    except ValueError:
        pass

    await s.redis.delete(inp.type + "_" + inp.token)
    
    return "success"


# TIMERS START ------

        
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
    a = len(s.open_jobs)
    b = len(s.closed_jobs)
    c = sum([s.leaderboard[i][1] for i in s.leaderboard])
    d = len(s.open_gpu)
    while True:
        await asyncio.sleep(300)
        
        w = len(s.open_jobs)
        if a != w:
            async with aiofiles.open("jobs/open.json", "w") as f:
                await f.write(json.dumps(s.open_jobs))
        x = len(s.closed_jobs)
        if b != x:
            async with aiofiles.open("jobs/closed.json", "w") as f:
                await f.write(json.dumps(s.closed_jobs))
        y = sum([s.leaderboard[i][1] for i in s.leaderboard])
        if c != y:
            async with aiofiles.open("jobs/leaderboard.json", "w") as f:
                await f.write(json.dumps(s.leaderboard))
        z = len(s.open_gpu)
        if d != z:
            async with aiofiles.open("jobs/open_gpu.json", "w") as f:
                await f.write(json.dumps(s.open_gpu))

        a = w
        b = x
        c = y
        

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
        async with aiofiles.open("jobs/open.json", "w") as f:
            await f.write(json.dumps(s.open_jobs))
        
        async with aiofiles.open("jobs/closed.json", "w") as f:
            await f.write(json.dumps(s.closed_jobs))
        
        async with aiofiles.open("jobs/leaderboard.json", "w") as f:
            await f.write(json.dumps(s.leaderboard))
        
        async with aiofiles.open("jobs/open_gpu.json", "w") as f:
            await f.write(json.dumps(s.open_gpu))

        
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


# ------------------------------ 


if __name__ == "__main__":
    run(app, host=HOST, port=PORT) #, workers=WORKERS_COUNT [multiprocessing was reverted for v2.1.0, will be added at a later date TBD]
