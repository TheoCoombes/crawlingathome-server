# Crawling@Home Server Configuration

# SERVER
HOST = "0.0.0.0"
PORT = 80
WORKERS_COUNT = 4 # Amount of CPU cores to dedicate to the server.

# WORKER CONFIG
IDLE_TIMEOUT = 5400 # The interval until a worker is kicked for being idle. (90 minutes)

# ETA CALCULATION
AVERAGE_INTERVAL = 900 # The interval for each measurement of the averages to take place. (15 minutes)
AVERAGE_DATASET_LENGTH = 10 # The maximum amount of measurements for the averages until older measurements are discarded.

# ADMIN
ADMIN_IPS = [
  "<YOUR IP HERE>"
]
