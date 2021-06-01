# Crawling@Home Server
A server powering distributed DALLE-pytorch dataset creation.
* Client Repo: [TheoCoombes/crawlingathome](https://drive.google.com/file/d/1XeIuFikFBt1lK49BDni3d5-EjeG75yAA/view?usp=sharing)
* Live Dashboard: http://crawlingathome.duckdns.org/

## UPDATE
`jobs/open.json` is now too big to store on GitHub. You can download it from [here](https://drive.google.com/file/d/1XeIuFikFBt1lK49BDni3d5-EjeG75yAA/view?usp=sharing).

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
