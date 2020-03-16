from Config import Config
from SubprocessExecutor import SubprocessExecutor

import logging
import random
import re

logger = logging.getLogger(__name__)

class ProxyService:
    @staticmethod
    def generate_proxy(idx=0, **kwargs):
        if not Config.use_proxy:
            logger.warning("Config.use_proxy has not been set. Proxy will not be generated.")
            return ""
        proxy = {
            'tor': ProxyService.generate_proxy_tor,
            'squid': ProxyService.generate_proxy_squid,
            'spysme': ProxyService.generate_proxy_spysme,
        }[Config.proxy_mode](idx, **kwargs)
        logger.debug(f"Generated proxy: {proxy}.")
        return proxy

    @staticmethod
    def generate_proxy_tor(idx, **kwargs):
        """ Needs tor running, see run_tor.sh """
        proxy_txt = "tor_list.txt"
        tor_proxy_regex = re.compile("socks5://(?P<host>\d+\.\d+\.\d+\.\d+):(?P<port>\d+)")
        with open(proxy_txt, 'r') as f:
            proxies_raw = f.read()
        proxies = list(map(lambda s: s.strip(), proxies_raw.split()))
        proxy = proxies[idx]
        regex_dict = tor_proxy_regex.match(proxy).groupdict()
        renew_identity_templ = lambda host, port: f""" bash -c 'echo -e "AUTHENTICATE \"\"\r\nsignal NEWNYM\r\nQUIT" | nc {host} {int(port) + 1} && sleep 5' """
        SubprocessExecutor.run_command(renew_identity_templ(regex_dict['host'], regex_dict['port']))
        return proxy
    
    @staticmethod
    def generate_proxy_squid(idx, **kwargs):
        """ Get the list from https://vip.squidproxies.com/index.php?action=assignedproxies """
        proxy_txt = "squid_list.txt"
        workers = kwargs['workers']
        list_chunker = lambda seq, size: tuple(seq[i::size] for i in range(size))
        with open(proxy_txt, 'r') as f:
            proxies_raw = f.read()
        proxies = list(map(lambda s: s.strip(), proxies_raw.split()))
        proxy_chunks = list_chunker(proxies, workers)
        proxy = random.choice(proxy_chunks[idx])
        return proxy

    @staticmethod
    def generate_proxy_spysme(_, **kwargs):
        proxy_command = 'curl "http://spys.me/proxy.txt"'
        proxy_result = SubprocessExecutor.run_command(proxy_command)
        raw_proxies = proxy_result['stdout'].strip().split("\n")
        proxies = [p[ :p.index(' ')] for p in raw_proxies if "-S" in p and " +" in p]
        proxy = random.choice(proxies)
        return proxy

if __name__ == '__main__':
    from LogFormatter import LogFormatter
    logger = LogFormatter.configure_root_logger()

    ip_command = "curl https://api.ipify.org"
    original_ip = SubprocessExecutor.run_command(ip_command)['stdout']
    proxy = ProxyService.generate_proxy_tor(0, workers=3)
    proxy_ip_command = f"{ip_command} --proxy {proxy}"
    proxy_ip = SubprocessExecutor.run_command(proxy_ip_command)['stdout']
    print(f"Original IP: {original_ip}\nProxy IP: {proxy_ip}")
    assert proxy_ip and original_ip != proxy_ip
