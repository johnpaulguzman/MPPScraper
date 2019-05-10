import json
import random

from Config import Config
from BaseExecutor import BaseExecutor

class ProxyService:
    def __init__(self):
        self.baseExecutor = BaseExecutor()

    def generate_proxy(self):
        proxy_command = "curl https://proxy.rudnkh.me/txt"
        proxy_result = self.baseExecutor.get_output(proxy_command)
        proxies = proxy_result.strip().split("\n")
        proxy = random.choice(proxies)
        return proxy


if __name__ == '__main__':
    proxyService = ProxyService()
    get_output = BaseExecutor().get_output
    ip_command = "curl https://api.ipify.org"
    original_ip = get_output(ip_command)
    proxy = proxyService.generate_proxy()
    proxy_ip_command = f"{ip_command} --proxy {proxy}"
    proxy_ip = get_output(proxy_ip_command)
    print(f"Original ip: {original_ip}\nProxy ip: {proxy_ip}")
