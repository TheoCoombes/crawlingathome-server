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
    return int(np.int64(job["end_id"]) / 1000000)

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
    directory = "https://commoncrawl.s3.amazonaws.com/"
    with open("jobs/original.json", "r") as f:
        db = json.load(f)
    with open("jobs/open.json", "r") as f:
        opened = [_calculate_shard_number(i) for i in db] 
    
    jobs = []
    
    for i in opened:
        data = db[i-1]
        job = Job(
            number=i,
            url=directory + data["url"],
            start_id=data["start_id"],
            end_id=data["end_id"],
            csv=False,
            csv_url=None,
            gpu=False,
            gpu_url=None,
            pending=False,
            closed=False,
            completor=None,
            cpu_completor=None,
            csv_completor=None
        )
        
        jobs.append(job)
    
    jobs = sorted(jobs, key=lambda x: x.number) # Sort
    
    
    print("Bulk creating jobs in database... (this may take a while)")
    await Job.bulk_create(jobs)
    
    del db, opened, closed, gpu_data, jobs
    gc.collect()
    
    
    print("Done.")



run_async(init())
