import json
from time import time

class DataLoader:
    def __init__(self, host=False):
        self._load()
        

    def _load(self):
        self.clients = {
            "HYBRID": {},
            "GPU": {},
            "CPU": {}
        }

        with open("jobs/shard_info.json", "r") as f:
            self.shard_info = json.load(f)

        with open("jobs/open.json", "r") as f:
            self.open_jobs = json.load(f)

        with open("jobs/closed.json", "r") as f:
            self.closed_jobs = json.load(f)

        with open("jobs/leaderboard.json", "r") as f:
            self.leaderboard = json.load(f)
        
        with open("jobs/open_gpu.json", "r") as f:
            self.open_gpu = json.load(f)

        self.pending_jobs = []
        self.pending_gpu = []

        self.total_jobs = self.shard_info["total_shards"]

        self.total_pairs = sum([self.leaderboard[i][1] for i in self.leaderboard])
        
        self.worker_cache = {
            "HYBRID": {},
            "GPU": {},
            "CPU": {}
        }
        
        self.jobs_remaining = len(self.open_jobs) - (len(self.pending_jobs) + len(self.closed_jobs))

        try:
            self.completion = (len(self.closed_jobs) / self.total_jobs) * 100
            self.progress_str = f"{len(self.closed_jobs):,} / {self.total_jobs:,}"
        except ZeroDivisionError:
            self.completion = 0.00
            self.progress_str = "0 / 0"

        self.eta = "N/A"

class GPUList:
    def __init__(self, ctime, nickname, display_name):
        self._data = {
            "jobs_completed": 0,
            "first_seen": ctime,
            "last_seen": ctime,
            "user_nickname": nickname,
            "display_name": display_name,
            "type": "GPU"
        }
        self._jobs = {
            "Waiting": "Initialized"
        }
    
    def newJob(self, shard_number):
        job = {
            "shard_number": shard_number,
            "progress": "Recieved new job"
        }
        self._jobs.append(job)
        self._data["last_seen"] = time()

    def updateProgress(self, shard_number, progress):
        self._jobs[shard_number] = progress
        self._data['last_seem'] = time()
    
    def completeJob(self, shard_number):
        del self._jobs[shard_number]
        self._data["jobs_completed"] += 1
        self._data["last_seen"] = time()

    def __getitem__(self, key):
        if key in self._data:
            return self._data[key]

        if key not in self._jobs[0]:
            raise KeyError(f'Key {key} not found')
        
        return ( job[key] for job in self._jobs )
    
    def __setitem__(self, key, value):
        if key in self._data:
            self._data[key] = value

        raise KeyError(f'Key {key} not found')
    
    def __len__(self):\
        return len(self._jobs)