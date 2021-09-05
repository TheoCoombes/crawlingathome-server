# Crawling@Home Server Configuration

# DATABASE CONFIG
SQL_CONN_URL = "postgres:///crawlingathome" # Example config for a postgres database. Works with any databases supported by Tortoise ORM.
REDIS_CONN_URL = "redis://127.0.0.1" # The Redis connection URL, used for caching webpages to avoid database strain.

# WORKER CONFIG
IDLE_TIMEOUT = 7200 # The interval, in seconds, until a worker is kicked for being idle. (default 2 hours)

# ETA CALCULATION
AVERAGE_INTERVAL = 900 # The interval for each measurement of the averages to take place. (default 15 minutes)
AVERAGE_DATASET_LENGTH = 10 # The maximum amount of measurements for the averages until older measurements are discarded.

# ADMIN
ADMIN_PASSWORD = "password"

# CACHE
PAGE_CACHE_EXPIRY = 30 # The number of seconds until the page cache is cleared and the page is re-rendered. (avoids database strain)

# UPLOAD ADDRESSES
UPLOAD_ADDRS = [
    "archiveteam@88.198.2.17::CAH"
]
UPLOAD_CPU_ADDRS = [
    "archiveteam@5.9.55.230::gpujobs"
]
