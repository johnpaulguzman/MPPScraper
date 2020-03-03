import random

from Config import Config
from BaseExecutor import BaseExecutor

class ProxyService:
    @staticmethod
    def generate_proxy():  # Taken from https://vip.squidproxies.com/index.php?action=assignedproxies
        if not Config.use_proxy:
            print ("Config.use_proxy has not been set. Proxy will not be generated.")
            return ""
        proxies_raw = """
170.130.58.171:8800
170.130.58.101:8800
        """ # socks5h://127.0.0.1:9060
        proxies = list(map(lambda s: s.strip(), proxies_raw.split()[1: ]))
        proxy = random.choice(proxies)
        print(f"Proxy: {proxy}")
        return proxy

    @staticmethod
    def generate_proxy_old():
        if not Config.use_proxy:
            print ("Config.use_proxy has not been set. Proxy will not be generated.")
            return ""
        proxy_command = 'curl "http://spys.me/proxy.txt"'
        proxy_result = BaseExecutor.run_command(proxy_command)
        raw_proxies = proxy_result['stdout'].strip().split("\n")
        proxies = [p[ :p.index(' ')] for p in raw_proxies if "-S" in p and " +" in p]
        proxy = random.choice(proxies)
        return proxy


if __name__ == '__main__':
    ip_command = "curl https://api.ipify.org"
    original_ip = BaseExecutor.run_command(ip_command)['stdout']
    proxy = ProxyService.generate_proxy()
    proxy_ip_command = f"{ip_command} --proxy {proxy}"
    proxy_ip = BaseExecutor.run_command(proxy_ip_command)['stdout']
    print(f"Original IP: {original_ip}\nProxy IP: {proxy_ip}")
    assert original_ip != proxy_ip
