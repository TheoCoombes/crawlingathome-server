# Crawling@Home Server
A server powering distributed DALLE-pytorch dataset creation.
* Client Repo: [TheoCoombes/crawlingathome](https://github.com/TheoCoombes/crawlingathome)

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
