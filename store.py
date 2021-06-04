import json

class DataLoader:
    def __init__(self):
        self._load()

    def _load(self):
        self.clients = {}

        with open("jobs/shard_info.json", "r") as f:
            self.shard_info = json.load(f)

        with open("jobs/open.json", "r") as f:
            self.open_jobs = json.load(f)

        with open("jobs/closed.json", "r") as f:
            self.closed_jobs = json.load(f)

        with open("jobs/leaderboard.json", "r") as f:
            self.leaderboard = json.load(f)

        self.pending_jobs = []

        self.total_jobs = self.shard_info["total_shards"]

        self.total_pairs = sum([self.leaderboard[i][1] for i in self.leaderboard])

        try:
            self.completion = (len(self.closed_jobs) / self.total_jobs) * 100
            self.progress_str = f"{len(self.closed_jobs):,} / {self.total_jobs:,}"
        except ZeroDivisionError:
            self.completion = 0.00
            self.progress_str = "0 / 0"

        self.eta = "N/A"
