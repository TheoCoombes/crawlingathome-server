from tortoise.models import Model
from tortoise import fields


# Models for interacting with the SQL database.
# Job -> pending=True -> pending=False, completed=True
# Job -> pending=True -> gpu=True, pending=False -> (same as above from pending=True)


class Job(Model):
    """ The SQL Hybrid open jobs table. """

    # The shard number.
    number = fields.IntField(pk=True)

    # The URL to download the shard from CommonCrawl.
    url = fields.CharField()

    # The starting and ending sample IDs for this entire chunk (= 2 shards)
    start_id = fields.CharField()
    end_id = fields.CharField()

    # The shard of the chunk: 0 = first 50%, 1 = last 50%.
    shard_of_chunk = fields.IntField()
    
    # Contains information about the shard's completion.
    pending = fields.BooleanField()
    gpu = fields.BooleanField()
    completed = fields.BooleanField()
    
    # Initially contains the worker's token whilst being processed, but contains the owner's nickname on completion.
    completor = fields.CharField()

    
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
    uuid = fields.CharField(pk=True)
    
    # The type of client. (HYBRID/CPU/GPU)
    type = fields.CharField()
    
    # User information.
    user_nickname = fields.CharField()
    
    # The shard this client is currently processing.
    shard = fields.ForeignKeyField("models.Job", related_name="worker")
    
    # Progress information sent from the client. ( client.log(...) )
    progress = fields.CharField(max_length=255)
    
    # How many jobs this client has completed
    jobs_completed = fields.IntField()
    
    # Client time information in a UTC epoch timestamp form. (helps with timeouts as well as calculating efficiency)
    first_seen = fields.IntField()
    last_seen = fields.IntField()
    
    def __str__(self):
        return self.type + " Client with UUID " + self.uuid

    

class Leaderboard(Model):
    """ The Hybrid/GPU job completion leaderboard. """
    
    # The user's nickname
    nickname = fields.CharField(pk=True)
    
    # Data about the user.
    jobs_completed = fields.IntField()
    pairs_scraped = fields.IntField()

    
class CPU_Leaderboard(Model):
    """ The CPU job completion leaderboard. """
    
    # The user's nickname
    nickname = fields.CharField(pk=True)
    
    # Data about the user.
    jobs_completed = fields.IntField()
