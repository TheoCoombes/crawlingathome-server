from tortoise.models import Model
from tortoise import fields


# Models for interacting with the SQL database.
# Job -> pending=True -> pending=False, closed=True
# Job -> pending=True -> gpu=True, pending=False -> (same as above from pending=True)


class Job(Model):
    """ The SQL Hybrid open jobs table. """

    # The shard number.
    number = fields.IntField(pk=True)

    # The URL to download the shard from CommonCrawl.
    url = fields.CharField(max_length=500)

    # The starting and ending sample IDs for this entire chunk (= 2 shards)
    start_id = fields.CharField(max_length=255)
    end_id = fields.CharField(max_length=255)

    # The shard of the chunk: 0 = first 50%, 1 = last 50%.
    shard_of_chunk = fields.IntField()
    
    # CSV information (not always used)
    csv = fields.BooleanField()
    csv_url = fields.CharField(max_length=500, null=True)
    
    # GPU job information (not always used)
    gpu = fields.BooleanField()
    gpu_url = fields.CharField(max_length=500, null=True)
    
    # Contains information about the shard's completion.
    pending = fields.BooleanField()
    closed = fields.BooleanField()
    
    # User data
    completor = fields.CharField(max_length=255, null=True) # Initially contains the worker's token whilst being processed, but contains the user's nickname on completion.
    csv_completor = fields.CharField(max_length=255, null=True) # (contains the CSV worker's user nickname on completion if this shard was also processed using a CSV worker)
    cpu_completor = fields.CharField(max_length=255, null=True) # (contains the CPU worker's user nickname on completion if this shard was also processed using a CPU worker)

    
    # The shard in string format (for debugging)
    def __str__(self):
        if self.completed:
            c = "Completed"
        elif self.pending:
            c = "Pending"
        else:
            c = "Open"
        return c + " job with shard number #" + str(self.number)

    
    
class Client(Model):
    """ The SQL Clients table. """
    
    # The UUID of the client.
    uuid = fields.CharField(max_length=255, pk=True)
    display_name = fields.CharField(max_length=255)
    
    # The type of client. (HYBRID/CPU/GPU)
    type = fields.CharField(max_length=6)
    
    # User information.
    user_nickname = fields.CharField(max_length=255)
    
    # The shard this client is currently processing.
    shard = fields.ForeignKeyField("models.Job", related_name="worker", null=True)
    
    # Progress information sent from the client. ( client.log(...) )
    progress = fields.CharField(max_length=255)
    
    # How many jobs this client has completed
    jobs_completed = fields.IntField()
    
    # Client time information in a UTC epoch timestamp form. (helps with timeouts as well as calculating efficiency)
    first_seen = fields.IntField()
    last_seen = fields.IntField()
    
    def __str__(self):
        return self.type + " Client with UUID " + self.uuid



class GPU_Leaderboard(Model):
    """ The GPU job completion leaderboard. """
    
    # The user's nickname
    nickname = fields.CharField(max_length=255, pk=True)
    
    # Data about the user.
    jobs_completed = fields.IntField(default=0)
    pairs_scraped = fields.IntField(default=0)

    
class CPU_Leaderboard(Model):
    """ The CPU job completion leaderboard. """
    
    # The user's nickname
    nickname = fields.CharField(max_length=255, pk=True)
    
    # Data about the user.
    jobs_completed = fields.IntField(default=0)
 

class CSV_Leaderboard(Model):
    """ The CSV job completion leaderboard. """
    
    # The user's nickname
    nickname = fields.CharField(max_length=255, pk=True)
    
    # Data about the user.
    jobs_completed = fields.IntField(default=0)


# CUSTOM SQL QUERIES:

CUSTOM_QUERY_GPU = """
UPDATE "job" 
SET pending=true, completor='{}' 
WHERE "number" IN 
    (
     SELECT "number" FROM "job" 
     WHERE pending=false AND closed=false AND gpu=true 
     ORDER BY RANDOM() LIMIT 1
     FOR UPDATE SKIP LOCKED
    )
  AND pending=false AND closed=false AND gpu=true
;
"""

CUSTOM_QUERY_CPU = """
UPDATE "job"
SET pending=true, completor='{}'
WHERE "number" IN 
    (
     SELECT "number" FROM "job" 
     WHERE pending=false AND closed=false AND gpu=false
     ORDER BY (CASE WHEN csv=true THEN -1 ELSE RANDOM() END) ASC
     LIMIT 1
     FOR UPDATE SKIP LOCKED
    )
  AND pending=false AND closed=false AND gpu=false
;
"""

CUSTOM_QUERY_CSV = """
UPDATE "job" 
SET pending=true, completor='{}' 
WHERE "number" IN 
    (
     SELECT "number" FROM "job" 
     WHERE pending=false AND closed=false AND gpu=false AND csv=false
     ORDER BY RANDOM() LIMIT 1
     FOR UPDATE SKIP LOCKED
    )
  AND pending=false AND closed=false AND gpu=false AND csv=false
;
"""
