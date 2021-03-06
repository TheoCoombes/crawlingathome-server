from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

import asyncio
from typing import Optional
from pydantic import BaseModel
from tortoise.transactions import in_transaction
from tortoise.contrib.fastapi import register_tortoise
from starlette.exceptions import HTTPException as StarletteHTTPException

from name import new as new_name
from random import choice
from requests import get
from uuid import uuid4
from time import time
import aiofiles
import json

from config import *
from models import *
from cache import Cache

    
app = FastAPI()
cache = Cache(REDIS_CONN_URL)
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
    url: str

class MarkAsDoneInput(BaseModel):
    password: str
    shards: list
    count: int
    nickname: str

class MarkAsDoneCPUInput(BaseModel):
    shards: list
    urls: dict
    nickname: str
    token: Optional[str] = None

class IsCompleteInput(BaseModel):
    addresses: list
        

# FRONTEND START ------


@app.get('/', response_class=HTMLResponse)
async def index(request: Request, all: Optional[bool] = False):
    try:
        body, expired = await cache.page.get_body_expired(f'/?all={all}')
        if not expired:
            return HTMLResponse(content=body)
        else:
            # Cache has expired, we need to re-render the page body.
            pass
    except:
        # Cache hasn't yet been set, we need to render the page body.
        pass
    
    # Render body
    
    completed = await Job.filter(closed=True).count()
    total = await Job.all().count()
    
    banner = await cache.client.get("banner")

    if not all:
        hybrid_clients = await Client.filter(type="HYBRID").prefetch_related("shard").order_by("first_seen").limit(50)
        cpu_clients = await Client.filter(type="CPU").prefetch_related("shard").order_by("first_seen").limit(50)
        gpu_clients = await Client.filter(type="GPU").prefetch_related("shard").order_by("first_seen").limit(50)
    else:
        hybrid_clients = await Client.filter(type="HYBRID").prefetch_related("shard").order_by("first_seen")
        cpu_clients = await Client.filter(type="CPU").prefetch_related("shard").order_by("first_seen")
        gpu_clients = await Client.filter(type="GPU").prefetch_related("shard").order_by("first_seen")
    
    len_hybrid = await Client.filter(type="HYBRID").count()
    len_cpu = await Client.filter(type="CPU").count()
    len_gpu = await Client.filter(type="GPU").count()
    
    total_pairs = await cache.client.get("pairs")
    total_ml_pairs = await cache.client.get("ml-pairs")
    total_nl_pairs = await cache.client.get("nl-pairs")
    
    if not total_pairs:
        total_pairs = "N/A"
    else:
        try:
            total_pairs = int(total_pairs)
        except ValueError:
            total_pairs = total_pairs.decode()
    
    if not total_ml_pairs:
        total_ml_pairs = "N/A"
    else:
        try:
            total_ml_pairs = int(total_ml_pairs)
        except ValueError:
            total_ml_pairs = total_ml_pairs.decode()
    
    if not total_nl_pairs:
        total_nl_pairs = "N/A"
    else:
        try:
            total_nl_pairs = int(total_nl_pairs)
        except ValueError:
            total_nl_pairs = total_nl_pairs.decode()
        
        
    body = templates.TemplateResponse('index.html', {
        "request": request,
        "all": all,
        "banner": banner,
        "hybrid_clients": hybrid_clients,
        "cpu_clients": cpu_clients,
        "gpu_clients": gpu_clients,
        "len_hybrid": len_hybrid,
        "len_cpu": len_cpu,
        "len_gpu": len_gpu,
        "completion_float": (completed / total) * 100 if total > 0 else 100.0,
        "completion_str": f"{completed:,} / {total:,}",
        "total_pairs": total_pairs,
        "total_multilanguage_pairs": total_ml_pairs,
        "total_nolang_pairs": total_nl_pairs,
        "eta": (await cache.client.get("eta")).decode()
    })

    # Set page cache with body.
    await cache.page.set(f'/?all={all}', body.body)

    return body
    


@app.get('/install', response_class=HTMLResponse)
async def install(request: Request):
    banner = await cache.client.get("banner")
    
    return templates.TemplateResponse('install.html', {
        "request": request,
        "banner": banner
    })


@app.get('/leaderboard', response_class=HTMLResponse)
async def leaderboard_page(request: Request):
    try:
        body, expired = await cache.page.get_body_expired('/leaderboard')
        if not expired:
            return HTMLResponse(content=body)
        else:
            # Cache has expired, we need to re-render the page body.
            pass
    except:
        # Cache hasn't yet been set, we need to render the page body.
        pass
    
    banner = await cache.client.get("banner")
    
    body = templates.TemplateResponse('leaderboard.html', {
        "request": request,
        "banner": banner,
        "leaderboard": await Leaderboard.all().order_by("-jobs_completed"),
        "cpu_leaderboard": await CPU_Leaderboard.all().order_by("-jobs_completed")
    })
    
    # Set page cache with body.
    await cache.page.set('/leaderboard', body.body)
    
    return body


@app.get('/worker/{type}/{display_name}', response_class=HTMLResponse)
async def worker_info(type: str, display_name: str, request: Request):
    type = type.upper()
    if type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
        
    banner = await cache.client.get("banner")
        
    try:
        data = await Client.get(display_name=display_name, type=type).prefetch_related("shard")
    except:
        raise HTTPException(status_code=404, detail="Worker not found.")
    
    return templates.TemplateResponse('worker.html', {"request": request, "c": data, "banner": banner})


@app.get('/data')
async def data():
    try:
        body, expired = await cache.page.get_body_expired('/data')
        if not expired:
            return json.loads(body)
        else:
            # Cache has expired, we need to re-render the page body.
            pass
    except:
        # Cache hasn't yet been set, we need to render the page body.
        pass
    
    
    total_pairs = await cache.client.get("pairs")
    total_ml_pairs = await cache.client.get("ml-pairs")
    
    if not total_pairs:
        total_pairs = "N/A"
    else:
        try:
            total_pairs = int(total_pairs)
        except ValueError:
            total_pairs = total_pairs.decode()
    
    if not total_ml_pairs:
        total_ml_pairs = "N/A"
    else:
        try:
            total_ml_pairs = int(total_ml_pairs)
        except ValueError:
            total_ml_pairs = total_ml_pairs.decode()
    
    
    completed = await Job.filter(closed=True).count()
    total = await Job.all().count()
    body = {
        "completion_str": f"{completed:,} / {total:,}",
        "completion_float": (completed / total) * 100 if total > 0 else 100.0,
        "total_connected_workers": await Client.all().count(),
        "total_pairs_scraped": total_pairs,
        "total_multilanguage_pairs_scraped": total_ml_pairs,
        "eta": (await cache.client.get("eta")).decode()
    }
    
    # Set page cache with body.
    await cache.page.set('/data', json.dumps(body))
    
    return body


@app.get('/worker/{type}/{display_name}/data')
async def worker_data(type: str, display_name: str):
    type = type.upper()
    if type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    
    try:
        c = await Client.get(display_name=display_name, type=type).prefetch_related("shard")
        return {
            "display_name": c.display_name,
            "shard_number": c.shard.number if c.shard else "N/A",
            "progress": c.progress,
            "jobs_completed": c.jobs_completed,
            "first_seen": c.first_seen,
            "last_seen": c.last_seen,
            "user_nickname": c.user_nickname,
            "type": c.type
        }
    except:
        raise HTTPException(status_code=404, detail="Worker not found.")
            
        
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


@app.get('/admin/set-banner', response_class=PlainTextResponse)
async def set_banner(password: str, text: str):
    if password == ADMIN_PASSWORD:
        if text.upper() == "RESET":
            await cache.client.delete("banner")
            return "reset banner"
        else:
            await cache.client.set("banner", text)
            return "done."
    else:
        return "invalid auth"

    
@app.get('/custom/get-cpu-wat', response_class=PlainTextResponse)
async def get_cpu_wat():
    async with in_transaction() as conn:
        data = await conn.execute_query_dict(
            """SELECT "url" FROM "job" WHERE closed=false AND pending=false AND gpu=false ORDER BY RANDOM() LIMIT 1;"""
        )
    return data[0]["url"]
    

@app.post('/custom/lookup-wat')
async def lookup_wat(inp: LookupWatInput):
    body = []
    
    shards = await Job.filter(closed=False, pending=False, gpu=False, url=inp.url)
    for shard in shards:
        body.append([
            shard.number,
            {
                "url": shard.url,
                "start_id": shard.start_id,
                "end_id": shard.end_id,
                "shard": shard.shard_of_chunk
            }
        ])
    
    if len(body) < 2:
        return {"status": "failed", "detail": "All/some shards have already been completed by another worker."}
    else:
        return {"status": "success", "shards": body}
    
    
@app.post('/custom/markasdone-cpu')
async def custom_markasdone(inp: MarkAsDoneCPUInput):
    existed = await Job.filter(number__in=inp.shards, closed=False, pending=False, gpu=False).count()
    jobs = await Job.filter(number__in=inp.shards, closed=False, pending=False, gpu=False)
    
    for job in jobs:
        job.cpu_completor = inp.nickname
        job.gpu = True
        job.gpu_url = inp.urls[str(job.number)]
        if "postgres" in job.gpu_url:
            job.gpu = False
            job.closed = True
        await job.save()
    
    if existed > 0:
        if inp.token:
            try:
                client = await Client.get(token=token)
                client.jobs_completed += existed
                client.last_seen = int(time())
                await client.save()
            except Exception:
                pass
            
        user, created = await CPU_Leaderboard.get_or_create(nickname=inp.nickname)
        
        if created:
            user.jobs_completed = existed
        else:
            user.jobs_completed += existed
        
        await user.save()
 
        return {"status": "success", "completed": existed}
    else:
        return {"status": "failed", "detail": "All shards have already been completed by another worker."}
    
    
@app.post('/custom/markasdone')
async def custom_markasdone(inp: MarkAsDoneInput):
    if inp.password != ADMIN_PASSWORD:
        return {"status": "failed", "detail": "Invalid password."}
    
    existed = await Job.filter(number__in=inp.shards, closed=False, pending=False).count()
    await Job.filter(number__in=inp.shards, closed=False, pending=False).update(closed=True, pending=False, completor=inp.nickname)
    
    if existed > 0:
        user, created = await Leaderboard.get_or_create(nickname=inp.nickname)
        
        if created:
            user.jobs_completed = existed
            user.pairs_scraped = inp.count
        else:
            user.jobs_completed += existed
            user.pairs_scraped += inp.count
        
        await user.save()
 
        return {"status": "success"}
    else:
        return {"status": "failed", "detail": "All shards have already been completed by another worker."}
 

@app.post('/api/isCompleted')
async def isCompleted(inp: IsCompleteInput):
    jobs = await Job.filter(gpu_url__in=inp.addresses, closed=True)
    closeds = [job.gpu_url for job in jobs]
    
    for addr in inp.addresses:
        if addr in closeds:
            continue
        elif not await Job.exists(gpu_url=addr):
            closeds.append(addr)
            
    return closeds


# API START ------


@app.get('/api/new')
async def new(nickname: str, type: Optional[str] = "HYBRID"):
    if type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    if type == "HYBRID":
        raise HTTPException(status_code=403, detail="Hybrid workers are no longer supported - consider creating a CPU worker instead.")
    
    uuid = str(uuid4())
    ctime = int(time())
    display_name = new_name()

    await Client.create(
        uuid=uuid,
        display_name=display_name,
        type=type,
        user_nickname=nickname,
        progress="Initialized",
        jobs_completed=0,
        first_seen=ctime,
        last_seen=ctime,
        shard=None
    )
    
    if type == "CPU":
        upload_addr = choice(UPLOAD_CPU_ADDRS)
    else:
        upload_addr = choice(UPLOAD_ADDRS)

    return {"display_name": display_name, "token": uuid, "upload_address": upload_addr}


@app.post('/api/validateWorker', response_class=PlainTextResponse)
async def validateWorker(inp: TokenInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
        
    exists = await Client.exists(uuid=inp.token, type=inp.type)
    
    return str(exists)


@app.get('/api/getUploadAddress', response_class=PlainTextResponse)
async def getUploadAddress(type: Optional[str] = "HYBRID"):
    if type == "CPU":
        return choice(UPLOAD_CPU_ADDRS)
    else:
        return choice(UPLOAD_ADDRS)


@app.post('/api/newJob')
async def newJob(inp: TokenInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    if inp.type == "HYBRID":
        raise HTTPException(status_code=403, detail="Hybrid workers are no longer supported - consider creating a CPU worker instead.")
    
    try:
        client = await Client.get(uuid=inp.token, type=inp.type).prefetch_related("shard")
    except:
        raise HTTPException(status_code=404, detail="The server could not find this worker. Did the worker time out?")
    
    if client.shard is not None and client.shard.pending:
        client.shard.pending = False
        await client.shard.save()

    if inp.type == "GPU":         
        try:
            # Empty out any existing jobs that may cause errors.
            await Job.filter(completor=client.uuid, pending=True).update(completor=None, pending=False)
            
            # We update with completor to be able to find the job and make it pending in a single request, and we later set it back to None.
            # This helps us avoid workers getting assigned the same job.
            # We also had to use a raw SQL query here, as tortoise-orm was not complex enough to allow us to perform this type of command.
            async with in_transaction() as conn:
                await conn.execute_query(
                    CUSTOM_QUERY_GPU.format(client.uuid)
                )
            job = await Job.get(completor=client.uuid, pending=True)
        except:
            raise HTTPException(status_code=403, detail="Either there are no new GPU jobs available, or there was an error whilst finding a job. Keep retrying, as GPU jobs are dynamically created.")
        
        job.completor = None
        await job.save()
        
        client.shard = job
        client.progress = "Recieved new job"
        client.last_seen = int(time())
        await client.save()
        
        return {"url": job.gpu_url, "start_id": job.start_id, "end_id": job.end_id, "shard": job.shard_of_chunk, "number": job.number}
    else:
        try:
            # Empty out any existing jobs that may cause errors.
            await Job.filter(completor=client.uuid, pending=True).update(completor=None, pending=False)
            
            # We update with completor to be able to find the job and make it pending in a single request, and we later set it back to None.
            # This helps us avoid workers getting assigned the same job.
            # We also had to use a raw SQL query here, as tortoise-orm was not complex enough to allow us to perform this type of command.
            async with in_transaction() as conn:
                await conn.execute_query(
                    CUSTOM_QUERY_CPU_HYBRID.format(client.uuid)
                )
            job = await Job.get(completor=client.uuid, pending=True)
        except:
            raise HTTPException(status_code=403, detail="Either there are no more jobs available, or an error occurred whilst finding a job.")
        
        job.completor = None
        await job.save()
        
        client.shard = job
        client.progress = "Recieved new job"
        client.last_seen = int(time())
        await client.save()      
        
        return {"url": job.url, "start_id": job.start_id, "end_id": job.end_id, "shard": job.shard_of_chunk, "number": job.number}


@app.get('/api/jobCount', response_class=PlainTextResponse)
async def jobCount(type: Optional[str] = "HYBRID"):
    if type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
        
    if type == "GPU":
        count = await Job.filter(pending=False, closed=False, gpu=True).count()
    else:
        count = await Job.filter(pending=False, closed=False, gpu=False).count()
    
    return str(count)


@app.post('/api/updateProgress', response_class=PlainTextResponse)
async def updateProgress(inp: TokenProgressInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    
    try:
        await Client.get(uuid=inp.token, type=inp.type).update(progress=inp.progress, last_seen=int(time()))
    except:
        raise HTTPException(status_code=404, detail="The server could not find this worker. Did the worker time out?")
    
    return "success"


@app.post('/api/markAsDone', response_class=PlainTextResponse)
async def markAsDone(inp: TokenCountInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    
    try:
        client = await Client.get(uuid=inp.token, type=inp.type).prefetch_related("shard")
    except:
        raise HTTPException(status_code=404, detail="The server could not find this worker. Did the worker time out?")
    
    if client.shard is None:
        raise HTTPException(status_code=403, detail="You do not have an open job.")
    if client.shard.closed:
        raise HTTPException(status_code=403, detail="This job has already been marked as completed!")
    
    if inp.type == "CPU":
        if inp.url is None:
            raise HTTPException(status_code=400, detail="The worker did not submit valid download data.")
        
        client.shard.gpu = True
        client.shard.pending = False
        client.shard.gpu_url = inp.url
        client.shard.cpu_completor = client.user_nickname
        if "postgres" in client.shard.gpu_url:
            client.shard.gpu = False
            client.shard.closed = True
        await client.shard.save()
        
        client.shard = None
        client.progress = "Completed Job"
        client.jobs_completed += 1
        client.last_seen = int(time())
        await client.save()

        user, created = await CPU_Leaderboard.get_or_create(nickname=client.user_nickname)
        if created:
            user.jobs_completed = 1
        else:
            user.jobs_completed += 1
            
        await user.save()
        
        # completion + completion_str are not affected by CPU jobs.
        
        return "success"
    else:
        if not inp.count:
            raise HTTPException(status_code=400, detail="The worker did not submit a valid count!")
        
        client.shard.closed = True
        client.shard.pending = False
        client.shard.completor = client.user_nickname
        await client.shard.save()
        
        client.shard = None
        client.progress = "Completed Job"
        client.jobs_completed += 1
        client.last_seen = int(time())
        await client.save()

        user, created = await Leaderboard.get_or_create(nickname=client.user_nickname)
        if created:
            user.jobs_completed = 1
            user.pairs_scraped = inp.count
        else:
            user.jobs_completed += 1
            user.pairs_scraped += inp.count
        
        await user.save()

        return "success"


@app.post('/api/gpuInvalidDownload', response_class=PlainTextResponse)
async def gpuInvalidDownload(inp: TokenInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    
    try:
        client = await Client.get(uuid=inp.token, type=inp.type).prefetch_related("shard")
    except:
        raise HTTPException(status_code=404, detail="The server could not find this worker. Did the worker time out?")
    
    if client.shard is None:
        raise HTTPException(status_code=403, detail="This worker is not currently working on a job.")
    
    client.shard.gpu_url = None
    client.shard.gpu = False
    client.shard.pending = False
    client.shard.cpu_completor = None
    await client.shard.save()
    
    client.shard = None
    client.last_seen = int(time())
    await client.save()
    
    return "success"

    
@app.post('/api/bye', response_class=PlainTextResponse)
async def bye(inp: TokenInput):
    if inp.type not in types:
        raise HTTPException(status_code=400, detail=f"Invalid worker type. Choose from: {types}.")
    
    try:
        client = await Client.get(uuid=inp.token, type=inp.type).prefetch_related("shard")
    except:
        raise HTTPException(status_code=404, detail="The server could not find this worker. Did the worker time out?")
        
    if client.shard != None:
        client.shard.pending = False
        await client.shard.save()
    
    await client.delete()
    
    return "success"


# TIMERS START ------


async def check_idle():
    while True:
        await asyncio.sleep(300)
        t = int(time()) - IDLE_TIMEOUT
        
        clients = await Client.filter(last_seen__lte=t, shard_id__not_isnull=True).prefetch_related("shard")
        for client in clients:
            if client.shard.pending:
                client.shard.pending = False
                await client.shard.save()
        
        await Client.filter(last_seen__lte=t).delete()

        
async def calculate_eta():
    await cache.client.set("eta", "Calculating...")
    
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
        try:
            start = await Job.filter(closed=True).count()
        except:
            await asyncio.sleep(5)
            continue
        await asyncio.sleep(AVERAGE_INTERVAL)
        end = await Job.filter(closed=True).count()

        dataset.append(end - start)
        if len(dataset) > AVERAGE_DATASET_LENGTH:
            dataset.pop(0)

        mean = sum(dataset) / len(dataset)
        mean_per_second = mean / AVERAGE_INTERVAL
        remaining = await Job.filter(closed=False, pending=False, gpu=False).count()

        try:
            length = remaining // mean_per_second
        except ZeroDivisionError:
            continue
        
        if length:
            await cache.client.set("eta", _format_time(length))
        else:
            await cache.client.set("eta", "Finished")


async def update_pairs_count():
    while True:
        await cache.client.set("pairs", 2323000000)
        await cache.client.set("ml-pairs", 2381000000)
        
        jsn = get("http://116.202.162.146:8000/info/?key=nolang").json()
        pairs = jsn.get("Number of items inserted", "N/A")
        await cache.client.set("nl-pairs", pairs)
        
        await asyncio.sleep(25)


# FASTAPI UTILITIES START ------ 
    
    
@app.on_event('startup')
async def app_startup():
    # Finds the worker number for this worker.
    await cache.initPID()
    
    if cache.iszeroworker:
        # The following functions only need to be executed on a single worker.
        asyncio.create_task(check_idle())
        asyncio.create_task(calculate_eta())
        asyncio.create_task(update_pairs_count())


@app.on_event('shutdown')
async def app_shutdown():
    await cache.safeShutdown()


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


# ------------------------------ 


register_tortoise(
    app,
    db_url=SQL_CONN_URL,
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)


if __name__ == "__main__":
    print("From v3.0.0, you can no longer run this script directly from Python. Call gunicorn/uvicorn directly from the terminal, using \"main:app\" as the server.")
