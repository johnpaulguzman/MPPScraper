import os
import sys

class Config:
    src_path = os.path.abspath(os.path.dirname(sys.argv[0]))
    data_path = os.path.join(*[src_path, "..", "..", "data"])
    use_proxy = True
    use_tor = True
    max_attempts = 30

if not os.path.exists(Config.data_path):
    os.makedirs(Config.data_path)
