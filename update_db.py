from tortoise import Tortoise, run_async
from config import SQL_CONN_URL
from models import *
import numpy as np
import json
import uuid
import gc

# JSON -> SQL CONVERTER SCRIPT -----
# You need a fresh `open.json` file named `original.json` stored in the jobs folder. (don't delete the existing open.json file)
# You need your SQL database set up, and configured in config.py

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
    
    jobs = []
    
    for i in range(9916):
        data = db[i-1]
        job = Job(
            number=uuid.uuid4().int,
            url=f"https://laion-humans.s3.amazonaws.com/humans/output/people-{i:06}.tar",
            pending=False,
            closed=False,
            completor=None
        )
        
        jobs.append(job)
    
    
    print("Bulk creating jobs in database... (this may take a while)")
    await Job.bulk_create(jobs)
    
    del db, opened, closed, gpu_data, jobs
    gc.collect()
    
    # We don't need to do Client as they are volatile
    # We don't need to do CPU_Leaderboard as it did not exist before v3.0.0
    
    print("Done.")



run_async(init())
