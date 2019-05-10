import random

from Config import Config
from BaseExecutor import BaseExecutor

class ProxyService:
    proxy_command = "curl -sSf https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"

    def __init__(self):
        self.baseExecutor = BaseExecutor()

    def generate_proxy(self):
        if not Config.use_proxy:
            print ("Config.use_proxy has not been set. Proxy will not be generated.")
            return ""
        proxy_result = self.baseExecutor.run_command(ProxyService.proxy_command)
        proxies = proxy_result['stdout'].strip().split("\n")
        proxy = random.choice(proxies)
        return proxy


if __name__ == '__main__':
    proxy_service = ProxyService()
    ip_command = "curl https://api.ipify.org"
    original_ip = proxy_service.baseExecutor.run_command(ip_command)['stdout']
    proxy = proxy_service.generate_proxy()
    proxy_ip_command = f"{ip_command} --proxy {proxy}"
    proxy_ip = proxy_service.baseExecutor.run_command(proxy_ip_command)['stdout']
    print(f"Original IP: {original_ip}\nProxy IP: {proxy_ip}")
