# Crawling@Home Server
A server powering Crawling@Home's effort to filter CommonCrawl with CLIP, building a large scale image-text dataset.
* Client Repo: [TheoCoombes/crawlingathome](https://github.com/TheoCoombes/crawlingathome)
* Live Server: http://crawlingathome.duckdns.org/

## UPDATE
`jobs/open.json` is now too big to store on GitHub. You can download it from [here](https://drive.google.com/file/d/1dQTmTjkoOkCQdNLVwCm4B-6uCQDpcvle/view?usp=sharing).

## Installation
```
git clone https://github.com/TheoCoombes/crawlingathome-server
cd crawlingathome-server
pip install -r requirements.txt
```

## Usage
The jobs data is already compiled for Common Crawl. To use, simply run `main.py`:
```
python main.py
```
You can edit the server's host and port by editing `config.py`.
