import os
import sys

class Config:
    src_path = os.path.abspath(os.path.dirname(sys.argv[0]))
    data_path = os.path.join(*[src_path, "..", "..", "data"])
    use_proxy = True
    max_attempts = 30
    timeout = 2.0
    # max_pages = 400
