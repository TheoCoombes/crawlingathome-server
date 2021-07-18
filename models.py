from tortoise.models import Model
from tortoise import fields


# Models for interacting with the SQL database.
# DIAGRAM
# Open_Jobs -> Pending_Jobs -> Closed_Jobs <---------¬
#                                  OR                |
#                             Open GPU jobs -> Pending GPU jobs

# Hybrid ---

class Open_Jobs(Model):
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


    # The shard in string format (for debugging)
    def __str__(self):
        return str(self.number)

    
class Pending_Jobs(Model):
    """ The SQL Hybrid pending jobs table.
    NOTE: programatically the same as the open jobs table. """

    # The shard number.
    number = fields.IntField(pk=True)

    # The URL to download the shard from CommonCrawl.
    url = fields.CharField()

    # The starting and ending sample IDs for this entire chunk (= 2 shards)
    start_id = fields.CharField()
    end_id = fields.CharField()

    # The shard of the chunk: 0 = first 50%, 1 = last 50%.
    shard_of_chunk = fields.IntField()


    # The shard in string format (for debugging)
    def __str__(self):
        return str(self.number)

    
class Closed_Jobs(Model):
    """ The SQL Hybrid pending jobs table.
    NOTE: programatically the same as the open jobs table. """

    # The shard number.
    number = fields.IntField(pk=True)

    # The URL to download the shard from CommonCrawl.
    url = fields.CharField()

    # The starting and ending sample IDs for this entire chunk (= 2 shards)
    start_id = fields.CharField()
    end_id = fields.CharField()

    # The shard of the chunk: 0 = first 50%, 1 = last 50%.
    shard_of_chunk = fields.IntField()


    # The shard in string format (for debugging)
    def __str__(self):
        return str(self.number)


# GPU ---

class Open_GPU(Model):
    """ The SQL GPU open jobs table. """

    # The shard number.
    number = fields.IntField(pk=True)

    # The path to download the shard - usually via rsync but could be from http(s).
    url = fields.CharField()

    # The starting and ending sample IDs for this entire chunk (= 2 shards)
    start_id = fields.CharField()
    end_id = fields.CharField()

    # The shard of the chunk: 0 = first 50%, 1 = last 50%.
    shard_of_chunk = fields.IntField()


    # The shard in string format (for debugging)
    def __str__(self):
        return str(self.number)


class Pending_GPU(Model):
    """ The SQL GPU pending jobs table. """

    # The shard number.
    number = fields.IntField(pk=True)

    # The path to download the shard - usually via rsync but could be from http(s).
    url = fields.CharField()

    # The starting and ending sample IDs for this entire chunk (= 2 shards)
    start_id = fields.CharField()
    end_id = fields.CharField()

    # The shard of the chunk: 0 = first 50%, 1 = last 50%.
    shard_of_chunk = fields.IntField()


    # The shard in string format (for debugging)
    def __str__(self):
        return str(self.number)
