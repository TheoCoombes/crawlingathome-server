# Crawling@Home Server
[![Discord Chat](https://img.shields.io/discord/823813159592001537?color=5865F2&logo=discord&logoColor=white)](https://discord.gg/dall-e)

A server powering Crawling@Home's effort to filter CommonCrawl with CLIP, building a large scale image-text dataset.
* Client Repo: [TheoCoombes/crawlingathome](https://github.com/TheoCoombes/crawlingathome)
* Worker Repo: [ARKSeal/crawlingathome-worker](https://github.com/ARKSeal/crawlingathome-worker)
* Live Server: http://crawlingathome.duckdns.org/

## Installation
1. Install requirements
```
git clone https://github.com/TheoCoombes/crawlingathome-server
cd crawlingathome-server
pip install -r requirements.txt
```
2. Setup Redis
   - [Redis Guide](https://www.digitalocean.com/community/tutorials/how-to-install-and-secure-redis-on-ubuntu-20-04)
   - Configure your Redis connection url in `config.py`.
3. Setup SQL database
   - [PostGreSQL Guide](https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-20-04) - follow steps 1-4, naming your database `crawlingathome`.
   - Install the required python library for the database you are using. (see link above)
   - Configure your SQL connection url in `config.py`.
   - In the `crawlingathome-server` folder, create a new folder named 'jobs', and download [this file](https://drive.google.com/file/d/1YiKlmisVJf1ngJv1weRFEaZrt74FSCbH/view?usp=sharing) there.
   - Also create two files there, named `closed.json`, `open_gpu.json` with the text `[]` stored in both.
   - Also create an extra file there named `leaderboard.json`, with the text `{}` stored.
   - Finally, create another file there named `shard_info.json` with the text `{"directory": "https://commoncrawl.s3.amazonaws.com/", "format": ".gz", "total_shards": 8569338}` stored.
   - You can then run `update_db.py` to setup the jobs database. (this may take a while)
4. Install ASGI server
   - From v3.0.0, you are required to start the server using a console command directly from the server backend.
   - You can either use `gunicorn` or `uvicorn`. Currently, the main production server uses `uvicorn` with 12 worker processes.
   - e.g. `uvicorn main:app --host 0.0.0.0 --port 80 --workers 12`


## Usage
As stated in step 4 of installation, you need to run the server using a console command directly from the ASGI server platform:
```
uvicorn main:app --host 0.0.0.0 --port 80 --workers 12
```
- *Runs the server through Uvicorn, using 12 processes.*
