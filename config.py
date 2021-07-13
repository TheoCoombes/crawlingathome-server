# Crawling@Home Server Configuration

# SERVER
HOST = "0.0.0.0"
PORT = 80
# WORKERS_COUNT = 4 # Amount of CPU cores to dedicate to the server. [NOT CURRENTLY WORKING]

# STORE CONFIG
# STORE_PASSWORD = "password" # Password used to access the store.
# STORE_PORT = 5000 # Store port.

# WORKER CONFIG
IDLE_TIMEOUT = 10800 # The interval until a worker is kicked for being idle. (3 hours)

# ETA CALCULATION
AVERAGE_INTERVAL = 900 # The interval for each measurement of the averages to take place. (15 minutes)
AVERAGE_DATASET_LENGTH = 10 # The maximum amount of measurements for the averages until older measurements are discarded.

# ADMIN
ADMIN_PASSWORD = "password"

# CACHE
MAX_WORKER_CACHE_SIZE = 250 # The max amount of {nickname: token} caches stored before early ones are erased. (for looking up workers' details)

# UPLOAD URLS
UPLOAD_URLS = [
    "archiveteam@88.198.2.17::CAH"
]
