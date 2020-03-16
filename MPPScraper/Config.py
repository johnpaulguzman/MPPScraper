import os
import sys


class Config:
    log_path = "scraper.log"
    src_path = os.path.abspath(os.path.dirname(sys.argv[0]))
    data_path = os.path.join(*[src_path, "..", "..", "data"])
    use_proxy = True
    proxy_mode = 'tor'
    max_attempts = 30

if not os.path.exists(Config.data_path):
    os.makedirs(Config.data_path)
