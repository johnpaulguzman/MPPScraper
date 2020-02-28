import random

from Config import Config
from BaseExecutor import BaseExecutor

class ProxyService:
    proxy_command = 'curl "http://spys.me/proxy.txt"'

    def __init__(self):
        self.baseExecutor = BaseExecutor()

    def generate_proxy(self):
        if not Config.use_proxy:
            print ("Config.use_proxy has not been set. Proxy will not be generated.")
            return ""
        proxy_result = self.baseExecutor.run_command(ProxyService.proxy_command)
        raw_proxies = proxy_result['stdout'].strip().split("\n")
        proxies = [p[ :p.index(' ')] for p in raw_proxies if "-S" in p and " +" in p]
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
