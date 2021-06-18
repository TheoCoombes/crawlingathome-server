from multiprocessing.managers import SyncManager
# from config import STORE_PASSWORD, STORE_PORT
import json

class Manager(SyncManager):
    pass

class DataLoader:
    def __init__(self, host=False):
        self._load()
        
        #if host:
        #    self._load()
        #    self._host()
        #else:
        #    self._connect()
    
    
#     def _host(self):
#         Manager.register("shard_info", self.shard_info)
#         Manager.register("open_jobs", self.open_jobs)
#         Manager.register("closed_jobs", self.closed_jobs)
#         Manager.register("leaderboard", self.leaderboard)
#         Manager.register("pending_jobs", self.pending_jobs)
#         Manager.register("total_jobs", self.total_jobs)
#         Manager.register("total_pairs", self.total_pairs)
#         Manager.register("worker_cache", self.worker_cache)
#         Manager.register("jobs_remaining", self.jobs_remaining)
#         Manager.register("completion", self.completion)
#         Manager.register("progress_str", self.progress_str)
#         Manager.register("eta", self.eta)
        
#         self.manager = Manager(("127.0.0.1", STORE_PORT), authkey=STORE_PASSWORD.encode())
#         self.manager.start()
    
#     def _connect(self):
#         self.manager = Manager(("127.0.0.1", STORE_PORT), authkey=STORE_PASSWORD.encode())
#         self.manager.connect()
        
#         Manager.register("shard_info")
#         Manager.register("open_jobs")
#         Manager.register("closed_jobs")
#         Manager.register("leaderboard")
#         Manager.register("pending_jobs")
#         Manager.register("total_jobs")
#         Manager.register("total_pairs")
#         Manager.register("worker_cache")
#         Manager.register("jobs_remaining")
#         Manager.register("completion")
#         Manager.register("progress_str")
#         Manager.register("eta")
        
#         self.shard_info = self.manager.shard_info()
#         self.open_jobs = self.manager.open_jobs()
#         self.closed_jobs = self.manager.closed_jobs()
#         self.leaderboard = self.manager.leaderboard()
#         self.pending_jobs = self.manager.pending_jobs()
#         self.total_jobs = self.manager.total_jobs()
#         self.total_pairs = self.manager.total_pairs()
#         self.worker_cache = self.manager.worker_cache()
#         self.jobs_remaining = self.manager.jobs_remaining()
#         self.completion = self.manager.completion()
#         self.progress_str = self.manager.progress_str()
#         self.eta = self.manager.eta()

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
        
        self.worker_cache = {}
        
        self.jobs_remaining = len(self.open_jobs) - (len(self.pending_jobs) + len(self.closed_jobs))

        try:
            self.completion = (len(self.closed_jobs) / self.total_jobs) * 100
            self.progress_str = f"{len(self.closed_jobs):,} / {self.total_jobs:,}"
        except ZeroDivisionError:
            self.completion = 0.00
            self.progress_str = "0 / 0"

        self.eta = "N/A"
