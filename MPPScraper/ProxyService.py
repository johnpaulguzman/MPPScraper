import re
import time

from Config import Config
from BaseExecutor import BaseExecutor


class ProxyService:
    @staticmethod
    def generate_proxy(idx=0):
        if not Config.use_proxy:
            print ("Config.use_proxy has not been set. Proxy will not be generated.")
            return ""
        proxy_txt = "proxy_list.txt"
        with open(proxy_txt, 'r') as f:
            proxies_raw = f.read()
        proxies = list(map(lambda s: s.strip(), proxies_raw.split()))
        proxy = proxies[idx]
        if Config.use_tor:
            regex_dict = re.match("socks5://(?P<host>\d+\.\d+\.\d+\.\d+):(?P<port>\d+)", proxy).groupdict()
            renew_identity_templ = lambda host, port: f""" bash -c 'echo -e "AUTHENTICATE \"\"\r\nsignal NEWNYM\r\nQUIT" | nc {host} {int(port) + 1}' """
            BaseExecutor.run_command(renew_identity_templ(regex_dict['host'], regex_dict['port']))
        time.sleep(10)  # wait for new proxy
        print(f"Generated proxy: {proxy}")
        return proxy
    
    """
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
    """

if __name__ == '__main__':
    ip_command = "curl https://api.ipify.org"
    original_ip = BaseExecutor.run_command(ip_command)['stdout']
    proxy = ProxyService.generate_proxy()
    proxy_ip_command = f"{ip_command} --proxy {proxy}"
    proxy_ip = BaseExecutor.run_command(proxy_ip_command)['stdout']
    print(f"Original IP: {original_ip}\nProxy IP: {proxy_ip}")
    assert original_ip != proxy_ip
