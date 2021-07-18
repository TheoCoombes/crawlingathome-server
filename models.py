from tortoise.models import Model
from tortoise import fields


# Models for interacting with the SQL database.
# DIAGRAM
# Open_Jobs -> Pending_Jobs -> Closed_Jobs <---------¬
#                                  OR                |
#                             Open GPU jobs -> Pending GPU jobs

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
    
    # Contains information about the current progress, if this shard is currently being completed.
    # 
    pending = fields.BooleanField()
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
    
    # The shard this client is currently processing.
    shard = fields.ForeignKeyField("models.Job")
    
    progress = fields.CharField(max_length=255)
    jobs_completed = fields.IntField()
    
    
