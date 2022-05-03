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


# REQUEST INPUTS START ------


class TokenInput(BaseModel):
    token: str

class TokenProgressInput(BaseModel):
    token: str
    progress: str

class TokenCountInput(BaseModel): # For marking as done
    token: str
    
    url: Optional[str] = None
    start_id: Optional[str] = None
    end_id: Optional[str] = None
    shard: Optional[int] = None

class AdminInput(BaseModel):
    password: str
    device_format: str
     
@app.post('/admin/kill-devices', response_class=PlainTextResponse)
async def bye(inp: AdminInput):
    if inp.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid Auth")
    
    await Client.filter(user_nickname__startswith=inp.device_format).update(kill=True)
    
    return "success"

        
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
        clients = await Client.all().prefetch_related("job").order_by("first_seen").limit(50)
    else:
        clients = await Client.all().prefetch_related("job").order_by("first_seen")
    
    len_clients = await Client.all().count()
        
    body = templates.TemplateResponse('index.html', {
        "request": request,
        "all": all,
        "banner": banner,
        "clients": clients,
        "len_clients": len_clients,
        "completion_float": (completed / total) * 100 if total > 0 else 100.0,
        "completion_str": f"{completed:,} / {total:,}",
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
        "leaderboard": await Leaderboard.all().order_by("-jobs_completed")
    })
    
    # Set page cache with body.
    await cache.page.set('/leaderboard', body.body)
    
    return body


@app.get('/worker/{display_name}', response_class=HTMLResponse)
async def worker_info(display_name: str, request: Request):      
    banner = await cache.client.get("banner")
        
    try:
        data = await Client.get(display_name=display_name).prefetch_related("job")
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
    
    completed = await Job.filter(closed=True).count()
    total = await Job.all().count()
    body = {
        "completion_str": f"{completed:,} / {total:,}",
        "completion_float": (completed / total) * 100 if total > 0 else 100.0,
        "total_connected_workers": await Client.all().count(),
        "eta": (await cache.client.get("eta")).decode()
    }
    
    # Set page cache with body.
    await cache.page.set('/data', json.dumps(body))
    
    return body


@app.get('/worker/{display_name}/data')
async def worker_data(display_name: str):    
    try:
        c = await Client.get(display_name=display_name).prefetch_related("job")
        return {
            "display_name": c.display_name,
            "shard_number": c.shard.number if c.shard else "N/A",
            "progress": c.progress,
            "jobs_completed": c.jobs_completed,
            "first_seen": c.first_seen,
            "last_seen": c.last_seen,
            "user_nickname": c.user_nickname
        }
    except:
        raise HTTPException(status_code=404, detail="Worker not found.")
            
        
# ADMIN START ------

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
   
# API START ------


@app.get('/api/new')
async def new(nickname: str):    
    uuid = str(uuid4())
    ctime = int(time())
    display_name = new_name()

    await Client.create(
        uuid=uuid,
        display_name=display_name,
        kill=False,
        user_nickname=nickname,
        progress="Initialized",
        jobs_completed=0,
        first_seen=ctime,
        last_seen=ctime,
        shard=None
    )
    
    upload_addr = choice(UPLOAD_ADDRS)

    return {"display_name": display_name, "token": uuid, "upload_address": upload_addr}


@app.post('/api/validateWorker', response_class=PlainTextResponse)
async def validateWorker(inp: TokenInput):
    exists = await Client.exists(uuid=inp.token)
    
    return str(exists)


@app.get('/api/getUploadAddress', response_class=PlainTextResponse)
async def getUploadAddress():
    return choice(UPLOAD_ADDRS)


@app.post('/api/newJob')
async def newJob(inp: TokenInput):    
    try:
        client = await Client.get(uuid=inp.token).prefetch_related("job")
    except:
        raise HTTPException(status_code=404, detail="The server could not find this worker. Did the worker time out?")
    
    if client.job is not None and client.job.pending:
        client.job.pending = False
        await client.job.save()
    
    try:
        # Empty out any existing jobs that may cause errors.
        await Job.filter(completor=client.uuid, pending=True).update(completor=None, pending=False)

        # We update with completor to be able to find the job and make it pending in a single request, and we later set it back to None.
        # This helps us avoid workers getting assigned the same job.
        # We also had to use a raw SQL query here, as tortoise-orm was not complex enough to allow us to perform this type of command.
        async with in_transaction() as conn:
            await conn.execute_query(
                CUSTOM_QUERY.format(client.uuid)
            )
        job = await Job.get(completor=client.uuid, pending=True)
    except:
        raise HTTPException(status_code=403, detail="Either there are no new jobs available, or there was an error whilst finding a job.")

    job.completor = None
    await job.save()

    client.job = job
    client.progress = "Recieved new job"
    client.last_seen = int(time())
    await client.save()

    return {"url": job.url, "number": job.number}


@app.get('/api/jobCount', response_class=PlainTextResponse)
async def jobCount(): 
    count = await Job.filter(pending=False, closed=False).count()
    return str(count)


@app.post('/api/updateProgress', response_class=PlainTextResponse)
async def updateProgress(inp: TokenProgressInput):
    try:
        await Client.get(uuid=inp.token).update(progress=inp.progress, last_seen=int(time()))
    except:
        raise HTTPException(status_code=404, detail="The server could not find this worker. Did the worker time out?")
    
    return "success"

@app.post('/api/shouldKill', response_class=PlainTextResponse)
async def shouldKill(inp: TokenInput):
    try:
        client = await Client.get(uuid=inp.token)
    except:
        raise HTTPException(status_code=404, detail="The server could not find this worker. Did the worker time out?")
    
    if client.kill:
        return "True"
    else:
        return "False"


@app.post('/api/markAsDone', response_class=PlainTextResponse)
async def markAsDone(inp: TokenCountInput):
    try:
        client = await Client.get(uuid=inp.token).prefetch_related("job")
    except:
        raise HTTPException(status_code=404, detail="The server could not find this worker. Did the worker time out?")
    
    if client.job is None:
        raise HTTPException(status_code=403, detail="You do not have an open job.")
    if client.job.closed:
        raise HTTPException(status_code=403, detail="This job has already been marked as completed!")

    client.job.closed = True
    client.job.pending = False
    client.job.completor = client.user_nickname
    await client.job.save()

    client.job = None
    client.progress = "Completed Job"
    client.jobs_completed += 1
    client.last_seen = int(time())
    await client.save()

    user, created = await Leaderboard.get_or_create(nickname=client.user_nickname)
    if created:
        user.jobs_completed = 1
    else:
        user.jobs_completed += 1

    await user.save()

    return "success"

    
@app.post('/api/bye', response_class=PlainTextResponse)
async def bye(inp: TokenInput):
    try:
        client = await Client.get(uuid=inp.token).prefetch_related("job")
    except:
        raise HTTPException(status_code=404, detail="The server could not find this worker. Did the worker time out?")
        
    if client.job != None:
        client.job.pending = False
        await client.job.save()
    
    await client.delete()
    
    return "success"


# TIMERS START ------


async def check_idle():
    while True:
        await asyncio.sleep(300)
        t = int(time()) - IDLE_TIMEOUT
        
        clients = await Client.filter(last_seen__lte=t).prefetch_related("job")
        for client in clients:
            if client.job is not None and client.job.pending:
                client.job.pending = False
                await client.job.save()
        
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
        remaining = await Job.filter(closed=False, pending=False).count()

        try:
            length = remaining // mean_per_second
        except ZeroDivisionError:
            continue
        
        if length:
            await cache.client.set("eta", _format_time(length))
        else:
            await cache.client.set("eta", "Finished")


# FASTAPI UTILITIES START ------ 
    
    
@app.on_event('startup')
async def app_startup():
    # Finds the worker number for this worker.
    await cache.initPID()
    
    if cache.iszeroworker:
        # The following functions only need to be executed on a single worker.
        asyncio.create_task(check_idle())
        asyncio.create_task(calculate_eta())


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
