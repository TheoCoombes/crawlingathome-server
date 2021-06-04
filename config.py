# Crawling@Home Server Configuration

# SERVER
HOST = "0.0.0.0"
PORT = 80
PROCESS_COUNT = 4 # Amount of CPU cores to dedicate to the server.

# WORKER CONFIG
IDLE_TIMEOUT = 5400 # The interval until a worker is kicked for being idle. (90 minutes)

# ETA CALCULATION
AVERAGE_INTERVAL = 1800 # The interval for each measurement of the averages to take place. (30 minutes)
AVERAGE_DATASET_LENGTH = 50 # The maximum amount of measurements for the averages until older measurements are discarded.

# ADMIN
ADMIN_IPS = [
  "<YOUR IP HERE>"
]
