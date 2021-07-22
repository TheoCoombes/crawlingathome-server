from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

import asyncio
from typing import Optional
from pydantic import BaseModel
from tortoise.contrib.fastapi import register_tortoise
from starlette.exceptions import HTTPException as StarletteHTTPException

from time import time, sleep
from random import choice
from uuid import uuid4
import numpy as np
import aiofiles
import json

from config import *
from models import *

    
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
async def index(request: Request):
    return templates.TemplateResponse('index.html', {"request": request, "all": all, "clients": s.clients, "completion": s.completion, "progress_str": s.progress_str, "total_pairs": s.total_pairs, "eta": s.eta})


@app.get('/install', response_class=HTMLResponse)
async def install(request: Request):
    return templates.TemplateResponse('install.html', {"request": request})


@app.get('/leaderboard', response_class=HTMLResponse)
async def leaderboard_page(request: Request):
    main_board = await Leaderboard.all()
    cpu_board = await CPU_Leaderboard.all()
    return templates.TemplateResponse('leaderboard.html', {"request": request, "leaderboard": board, "cpu_leaderboard": cpu_board})


@app.get('/worker/{type}/{token}', response_class=HTMLResponse)
async def worker_info(type: str, token: str, request: Request):
    type = type.upper()
    if type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
        
    try:
        data = await Client.get(uuid=token, type=type).prefetch_related("shard")
    except:
        raise HTTPException(status_code=500, detail="Worker not found.")
    
    return templates.TemplateResponse('worker.html', {"request": request, "c": data})


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
        c = await Client.get(uuid=token, type=type).prefetch_related("shard")
        return {
            "shard_number": c.shard.number,
            "progress": c.progress,
            "jobs_completed": c.jobs_completed,
            "first_seen": c.first_seen,
            "last_seen": c.last_seen,
            "user_nickname": c.user_nickname,
            "type": c.type
        }
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
    
    body = []
    
    shards = await Job.filter(closed=False, pending=False, gpu=False, url=inp.url)
    async for shard in shards:
        body.append([
            shard.number,
            {
                "url": shard.url,
                "start_id": shard.start_id,
                "end_id": shard.end_id,
                "shard": shard.shard_of_chunk
            }
        ])
    
    if len(shards) == 0:
        return {"status": "failed", "detail": "All shards have already been completed by another worker."}
    else:
        return {"status": "success", "shards": shards}
    
    
@app.post('/custom/markasdone')
async def custom_markasdone(inp: MarkAsDoneInput):
    if inp.password != ADMIN_PASSWORD:
        return {"status": "failed", "detail": "Invalid password."}
    
    existed = 0
    shards = await Job.filter(number__in=inp.shards, closed=False, pending=False)
    
    existed = shards.count()
    await shards.update(closed=True, pending=False, gpu=False, completor=inp.nickname)
    
    if existed > 0:
        user = await Leaderboard.get_or_create(nickname=inp.nickname)
        
        job_count = user.job_count += existed
        pairs_scraped = user.pairs_scraped += inp.count
        
        await user.update(job_count=job_count, pairs_scraped=pairs_scraped)

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
    
    uuid = str(uuid4())
    ctime = int(time())

    worker_data = {
        "uuid": uuid,
        "type": type,
        "user_nickname": nickname,
        "progress": "Initialized",
        "jobs_completed": 0,
        "first_seen": ctime,
        "last_seen": ctime,
        "shard": None
    }
    
    await Client.create(**worker_data)

    return {"display_name": uuid, "token": uuid, "upload_address": choice(UPLOAD_URLS)}


@app.post('/api/validateWorker', response_class=PlainTextResponse)
async def validateWorker(inp: TokenInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    return str(await Client.exists(uuid=inp.token, type=inp.type))


@app.get('/api/getUploadAddress', response_class=PlainTextResponse)
async def getUploadAddress():
    return choice(UPLOAD_URLS)


@app.post('/api/newJob')
async def newJob(inp: TokenInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    
    try:
        client = await Client.get(uuid=inp.token, type=inp.type).prefetch_related("shard")
    except:
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?")
    
    if client.shard is not None:
        await client.shard.update(pending=False, completor=None)
    
    if inp.type == "GPU":         
        try:
            job = await Job.filter(pending=False, closed=False, gpu=True).first()
        except:
            raise HTTPException(status_code=503, detail="No new GPU jobs available. Keep retrying, as GPU jobs are dynamically created.")
        
        await job.update(pending=True, completor=inp.token)
        await client.update(progress="Recieved new job", shard=job, last_seen=int(time()))
        
        return {"url": job.gpu_url, "start_id": job.start_id, "end_id": job.end_id, "shard": job.shard}
    else:
        try:
            job = await Job.filter(pending=False, closed=False, gpu=False).first()
        except:
            raise HTTPException(status_code=503, detail="No new GPU jobs available. Keep retrying, as GPU jobs are dynamically created.")
        
        await job.update(pending=True, completor=inp.token)
        await client.update(progress="Recieved new job", shard=job, last_seen=int(time()))
        
        return {"url": job.url, "start_id": job.start_id, "end_id": job.end_id, "shard": job.shard}


@app.get('/api/jobCount', response_class=PlainTextResponse)
async def jobCount(type: Optional[str] = "HYBRID"):
    if type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
        
    if type == "GPU":
        return str(await Job.filter(gpu=True, closed=False, pending=False).count())
    else:
        return str(await Job.filter(gpu=False, closed=False, pending=False).count())


@app.post('/api/updateProgress', response_class=PlainTextResponse)
async def updateProgress(inp: TokenProgressInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    
    try:
        await Client.get(uuid=inp.token, type=inp.type).update(progress=inp.progress, last_seen=int(time()))
    except:
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?")
    
    return "success"


@app.post('/api/markAsDone', response_class=PlainTextResponse)
async def markAsDone(inp: TokenCountInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    
    try:
        client = await Client.get(uuid=inp.token, type=inp.type).prefetch_related("shard")
    except:
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?")
    
    if client.shard is None:
        raise HTTPException(status_code=500, detail="You do not have an open job.")
    if client.shard.closed:
        raise HTTPException(status_code=500, detail="This job has already been marked as completed!")
    
    if inp.type == "CPU":
        if inp.url is None or inp.start_id is None or inp.end_id is None or inp.shard is None:
            raise HTTPException(status_code=500, detail="The worker did not submit valid input data.")
        
        await client.shard.update(gpu=True, pending=False, gpu_url=inp.url, cpu_completor=client.user_nickname)
        await client.update(shard=None, progress="Completed Job", last_seen=int(time()), jobs_completed=(client.jobs_completed+1))

        user = await Leaderboard_CPU.get_or_create(nickname=client.user_nickname)
        
        job_count = user.job_count += 1
        
        await user.update(job_count=job_count)
        
        return "success"
    else:
        if not inp.count:
            raise HTTPException(status_code=500, detail="The worker did not submit a valid count!")
        
        await client.shard.update(closed=True, pending=False, completor=client.user_nickname)
        await client.update(shard=None, progress="Completed Job", last_seen=int(time()), jobs_completed=(client.jobs_completed+1))

        user = await Leaderboard.get_or_create(nickname=client.user_nickname)
        
        job_count = user.job_count += 1
        pairs_scraped = user.pairs_scraped += inp.count
        
        await user.update(job_count=job_count, pairs_scraped=pairs_scraped)

        return "success"


@app.post('/api/gpuInvalidDownload', response_class=PlainTextResponse)
async def gpuInvalidDownload(inp: TokenInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    if not await s.redis.exists(inp.type + "_" + inp.token):
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?")
    
    try:
        client = await Client.get(uuid=inp.token, type=inp.type).prefetch_related("shard")
    except:
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?")
    
    await client.shard.update(gpu_url=None, gpu=False, pending=False, completor=None)
    await client.update(shard=None, last_seen=int(time()))
    
    return "success"

    
@app.post('/api/bye', response_class=PlainTextResponse)
async def bye(inp: TokenInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    
    try:
        client = await Client.get(uuid=inp.token, type=inp.type).prefetch_related("shard")
    except:
        raise HTTPException(status_code=500, detail="The server could not find this worker. Did the server just restart?")
        
    if client.shard != None:
        await client.shard.update(pending=False)
    
    await client.delete()
    
    return "success"


# TIMERS START ------


async def check_idle():
    while True:
        await asyncio.sleep(300)
        t = int(time()) - IDLE_TIMEOUT
        
        await Client.filter(last_seen__lte=t, shard__not_isnull=True).select_related("shard").update(pending=False)
        await Client.filter(last_seen__lte=t).delete()

        
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
        d = z
        

# FASTAPI UTILITIES START ------ 
    
    
@app.on_event('startup')
async def app_startup():
    if __name__ == "__main__":
        asyncio.create_task(check_idle())
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


register_tortoise(
    app,
    db_url=SQL_DB_URL,
    modules={"models": ["app_db"]},
    generate_schemas=True,
    add_exception_handlers=True,
)


if __name__ == "__main__":
    print("From v3.0.0, you can no longer run this script directly from Python. Use gunicorn/uvicorn directly, using \"main:app\" as the server.")
