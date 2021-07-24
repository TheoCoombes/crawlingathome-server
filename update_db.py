from tortoise import Tortoise, run_async
from config import SQL_CONN_URL
from models import *
import numpy as np
import json
import gc

# JSON -> SQL CONVERTER SCRIPT -----
# You need a fresh `open.json` file named `original.json` stored in the jobs folder. (don't delete the existing open.json file)
# You need your SQL database set up, and configured in config.py

def _calculate_shard_number(job):
    count = (np.int64(job["end_id"]) / 1000000) * 2
    if job["shard"] == 0:
        count -= 1
    return int(count)

async def init():
    # 0. Connect to DB
    print("Connecting to DB using url from config.py...")
    await Tortoise.init(
        db_url=SQL_CONN_URL,
        modules={'models': ['models']}
    )

    await Tortoise.generate_schemas()
    
    
    # 1. Jobs
    print("Processing jobs... (this may take a while)")
    with open("jobs/shard_info.json", "r") as f:
        directory = json.load(f)["directory"]
    with open("jobs/original.json", "r") as f:
        db = json.load(f)
    with open("job/open.json", "r") as f:
        opened = [_calculate_shard_number(i) for i in json.load(f)] 
    with open("jobs/closed.json", "r") as f:
        closed = [int(i) for i in json.load(f)]
    with open("jobs/open_gpu", "r") as f:
        gpu_data = json.load(f)
    
    jobs = []
    
    for i in opened:
        data = db[i-1]
        job = Job(
            number=i,
            url=directory + data["url"],
            start_id=data["start_id"],
            end_id=data["end_id"],
            shard_of_chunk=data["shard"],
            gpu=False,
            gpu_url=None,
            pending=False,
            closed=False,
            completor=None,
            cpu_completor=None
        )
        
        jobs.append(job)
    
    for i in closed:
        data = db[i-1]
        job = Job(
            number=i,
            url=directory + data["url"],
            start_id=data["start_id"],
            end_id=data["end_id"],
            shard_of_chunk=data["shard"],
            gpu=False,
            gpu_url=None,
            pending=False,
            closed=True,
            completor="N/A",
            cpu_completor=None
        )
        
        jobs.append(job)
    
    for data in gpu_data:
        number = int(data[0])
        job = Job(
            number=number,
            url=directory + db[number-1]["url"],
            start_id=data[1]["start_id"],
            end_id=data[1]["end_id"],
            shard_of_chunk=data[1]["shard"],
            gpu=True,
            gpu_url=data[1]["url"],
            pending=False,
            closed=False,
            completor=None,
            cpu_completor="N/A"
        )
        
        jobs.append(job)
    
    jobs = sorted(jobs, key=lambda x: x.number)
    
    print("Bulk creating jobs in database... (this may take a while)")
    await Job.bulk_create(jobs)
    
    del db, opened, closed, gpu_data, jobs
    gc.collect()
    
    
    # 2. Leaderboard
    print("Processing leaderboard...")
    with open("jobs/leaderboard.json", "r") as f:
        lb = json.load(f)
    
    leaderboard = []
    
    for user in lb:
        userboard = Leaderboard(
            nickname=user,
            jobs_completed=lb[user][0],
            pairs_scraped=lb[user][1]
        )
        
        leaderboard.append(userboard)
    
    print("Bulk creating leaderboard in database... (this may take a while)")
    await Leaderboard.bulk_create(leaderboard)
    
    del lb, leaderboard
    gc.collect()
    
    
    # We don't need to do Client as they are volatile
    # We don't need to do CPU_Leaderboard as it did not exist before v3.0.0
    
    print("Done.")



run_async(init())
