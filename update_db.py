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
    count = 0
    
    for i in range(128):
        for i2 in range(354):
            job = Job(
                number=count+1,
                url=f"https://huggingface.co/datasets/laion/laion2B-multi-joined/resolve/main/part-{i:05}-fcd86c9b-36f4-49ff-bea1-8c9a0e029fb7-c000.snappy.parquet:{(i2+1):03}",
                pending=False,
                closed=False,
                completor=None
            )
            
            count += 1
            jobs.append(job)
    
    
    print("Bulk creating jobs in database... (this may take a while)")
    await Job.bulk_create(jobs)
    
    # We don't need to do Client as they are volatile
    # We don't need to do CPU_Leaderboard as it did not exist before v3.0.0
    
    print("Done.")



run_async(init())
