import json
from time import time

class DataLoader:
    def __init__(self):
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
        
        self.jobs_remaining = str(len(self.open_jobs) - (len(self.pending_jobs) + len(self.closed_jobs)))

        try:
            self.completion = (len(self.closed_jobs) / self.total_jobs) * 100
            self.progress_str = f"{len(self.closed_jobs):,} / {self.total_jobs:,}"
        except ZeroDivisionError:
            self.completion = 0.00
            self.progress_str = "0 / 0"

        self.eta = "N/A"
