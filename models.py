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
    
    # Contains information about the shard's completion.
    pending = fields.BooleanField()
    closed = fields.BooleanField()
    
    # User data
    completor = fields.CharField(max_length=255, null=True) # Initially contains the worker's token whilst being processed, but contains the user's nickname on completion.

    
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
    kill = fields.BooleanField()
    
    # User information.
    user_nickname = fields.CharField(max_length=255)
    
    # The shard this client is currently processing.
    job = fields.ForeignKeyField("models.Job", related_name="worker", null=True)
    
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
    nickname = fields.CharField(max_length=255, pk=True)
    
    # Data about the user.
    jobs_completed = fields.IntField(default=0)

    
# CUSTOM SQL QUERIES:

CUSTOM_QUERY = """
UPDATE "job" 
SET pending=true, completor='{}' 
WHERE "number" IN 
    (
     SELECT "number" FROM "job" 
     WHERE pending=false AND closed=false
     ORDER BY RANDOM() LIMIT 1
     FOR UPDATE SKIP LOCKED
    )
  AND pending=false AND closed=false
;
"""
