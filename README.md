# Crawling@Home Server
A server powering Crawling@Home's effort to filter CommonCrawl with CLIP, building a large scale image-text dataset.
* Client Repo: [TheoCoombes/crawlingathome](https://github.com/TheoCoombes/crawlingathome)
* Worker Repo: [Wikidepia/crawlingathome-worker](https://github.com/Wikidepia/crawlingathome-worker)
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
   - You can use any database supported by Tortoise ORM. [View All](https://tortoise-orm.readthedocs.io/en/latest/#pluggable-database-backends)
   - [PostGreSQL Guide] - follow steps 1-4, naming your database `crawlingathome`.
   - Install the required python library for the database you are using. (see link above)
   - Configure your SQL connection url in `config.py`.
   - In the `crawlingathome-server` folder, create a new folder named 'jobs', and download [this file](https://drive.google.com/file/d/1YiKlmisVJf1ngJv1weRFEaZrt74FSCbH/view?usp=sharing) there.
   - You can then run `update_db.py` to setup the jobs database. (this may take a while)
4. Install ASGI server
   - From v3.0.0, you are required to start the server using a console command directly from the server backend.
   - You can either use `gunicorn` or `uvicorn`. I'd personally reccomend using `gunicorn` with the `uvicorn` worker class.
   - e.g. `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`


## Usage
As stated in step 4 of installation, you need to run the server using a console command directly from the ASGI server platform:
```
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```
*Runs the server using 4 threads and the uvicorn worker class.*
