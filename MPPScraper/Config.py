import os
import sys

class Config:
    src_path = os.path.abspath(os.path.dirname(sys.argv[0]))
    data_path = os.path.join(*[src_path, "..", "..", "data"])
    use_proxy = True
    max_attempts = 20
    timeout = 1.5
    wait_time = None
