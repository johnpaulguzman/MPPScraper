import itertools
import pandas as pd
import random

from EnhancedExecutor import CommandTemplate, CommandEnhancer, EnhancedExecutor
from ProxyService import ProxyService


def tuple_stats(name, generator, peek=2):
    tup = tuple(generator)
    print(f">> {name} = {tup[ :peek]}, ... {tup[-peek: ]}\n   length = {len(tup)}\n")
    return tup

code_csv = pd.read_csv("airport_codes.csv")
code_range = code_csv['Code'].to_list()
code_combinations = ((c1, c2) for c1 in code_range for c2 in code_range if c1 != c2)

(range_days, range_weeks, range_months) = (0, 1, 0)
date_start = pd.to_datetime('today')
date_end = date_start + pd.DateOffset(days=range_days, weeks=range_weeks, months=range_months)
date_range = pd.date_range(date_start, date_end)
roundtrip_combinations = ((str(d1.date()), str(d2.date())) for d1 in date_range for d2 in date_range if d1 < d2)
oneway_combinations = ((str(d.date()), None) for d in date_range)
date_combinations = itertools.chain(oneway_combinations, roundtrip_combinations)

### cabin_class_combinations = (('economy', ), ('premium', ), ('business', ), ('first', ))
cabin_class_combinations = (('economy', ), ) ###### TEMP LIMIT ######

### max_adults = 9
### max_children = 7
(max_adults, max_children) = (3, 2)  ###### TEMP LIMIT ######
adults_range = range(0, max_adults + 1)
seniors_range = range(0, max_adults + 1)
lap_infants_range = range(0, max_children + 1)
seat_infants_range = range(0, max_children + 1)
child_range = range(0, max_children + 1)
youth_range = range(0, max_children + 1)
travellers_combinations = ((adult, senior, lap_infant, seat_infant, child, youth) \
                            for adult in adults_range \
                            for senior in seniors_range \
                            for lap_infant in lap_infants_range \
                            for seat_infant in seat_infants_range \
                            for child in child_range \
                            for youth in youth_range \
                            if 0 < (adult + senior) <= max_adults and \
                                (lap_infant + seat_infant + child + youth) <= max_children)

max_carryon_bags = 1
max_checked_bags = 2
carryon_bags_range = range(0, max_carryon_bags + 1)
checked_bags_range = range(0, max_checked_bags + 1)
bags_combinations = ((carryon, checked) for carryon in carryon_bags_range for checked in checked_bags_range)

code_combinations = tuple_stats("code_combinations", code_combinations)
date_combinations = tuple_stats("date_combinations", date_combinations)
cabin_class_combinations = tuple_stats("cabin_class_combinations", cabin_class_combinations)
travellers_combinations = tuple_stats("travellers_combinations", travellers_combinations)
bags_combinations = tuple_stats("bags_combinations", bags_combinations)

code_combinations = random.sample(code_combinations, 1)#5)
date_combinations = random.sample(date_combinations, 1)#4)
cabin_class_combinations = random.sample(cabin_class_combinations, 1)
travellers_combinations = random.sample(travellers_combinations, 1)#3)
bags_combinations = random.sample(bags_combinations, 1)

codes_templ = lambda code_origin, code_destination: f"{code_origin}-{code_destination}"
dates_templ = lambda date_departure, date_return: f"{date_departure}" if date_return is None else f"{date_departure}/{date_return}"
travellers_templ = lambda adults, seniors, lap_infants, seat_infants, children, youth: f"{adults}adults/{seniors}seniors/children{'-1S' * seat_infants}{'-1L' * lap_infants}{'-11' * children}{'-17' * youth}"
bags_templ = lambda carryon_bags, checked_bags: f"fs=cfc={carryon_bags};bfc={checked_bags}"
def search_templ(code_origin, code_destination, date_departure, date_return, cabin_class, adults, seniors, \
        lap_infants, seat_infants, children, youth, carryon_bags, checked_bags, sort='price_a'):
    """ Sample format: https://www.kayak.com/flights/MNL-SYD/2020-03-19/2020-03-26/business/1adults/1seniors/children-1S-1L-1L-11-17?fs=cfc=1;bfc=2&sort=price_a """
    codes = codes_templ(code_origin, code_destination)
    dates = dates_templ(date_departure, date_return)
    travellers = travellers_templ(adults, seniors, lap_infants, seat_infants, children, youth)
    bags = bags_templ(carryon_bags, checked_bags)
    return f"""curl "https://www.kayak.com/flights/{codes}/{dates}/{cabin_class}/{travellers}?{bags}&sort={sort} \
        -H 'authority: www.kayak.com' \
        -H 'cache-control: max-age=0' \
        -H 'upgrade-insecure-requests: 1' \
        -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36' \
        -H 'sec-fetch-dest: document' \
        -H 'accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9' \
        -H 'sec-fetch-site: same-origin' \
        -H 'sec-fetch-mode: navigate' \
        -H 'sec-fetch-user: ?1' \
        -H 'accept-language: en-US,en;q=0.9' \
        --compressed"""

kayak_command_templ = CommandTemplate(search_templ, code_combinations, date_combinations, \
    cabin_class_combinations, travellers_combinations, bags_combinations, nested=True)
search_combinations = kayak_command_templ.build()
search_combinations = tuple_stats("search_combinations", search_combinations)

#######################################################################################################################

proxy_service = ProxyService()
initializer = proxy_service.generate_proxy
def decorator(c, p):
    return f"{c} --proxy {p}" if p is not None else c
curl_proxy_decorator = CommandEnhancer(initializer, decorator)

#######################################################################################################################

workers = 30
enhancedExecutor = EnhancedExecutor(kayak_command_templ, curl_proxy_decorator, workers)
results = enhancedExecutor.run_commands_on_workers()

#######################################################################################################################

import code; code.interact(local={**locals(), **globals()}) ## INTERACT

'''
    test_command = """
    curl 'https://www.kayak.com/flights/JAX-SIN/2020-02-28/2020-03-12/1adults/children-1S-1L?sort=price_a' \
        -H 'authority: www.kayak.com' \
        -H 'cache-control: max-age=0' \
        -H 'upgrade-insecure-requests: 1' \
        -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36' \
        -H 'sec-fetch-dest: document' \
        -H 'accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9' \
        -H 'sec-fetch-site: same-origin' \
        -H 'sec-fetch-mode: navigate' \
        -H 'sec-fetch-user: ?1' \
        -H 'accept-language: en-US,en;q=0.9' \
        --compressed
    """
    test = base_executor.run_command(test_command)
    import code; code.interact(local={**locals(), **globals()}) ## INTERACT
"""
from bs4 import BeautifulSoup

test = base_executor.run_command(test_command)
soup1 = BeautifulSoup(test['stdout'], 'html.parser')
z1 = soup1.find_all('div', {'class': 'resultWrapper'})



from selenium import webdriver
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
# chrome_options.add_argument("--headless")
driver = webdriver.Chrome(chrome_options=chrome_options)

driver.get('https://www.kayak.com/flights/JAX-SIN/2020-02-28/2020-03-12/1adults/children-1S-1L?sort=price_a')
soup2 = BeautifulSoup(driver.page_source, 'html.parser')
z2 = soup2.find_all('div', {'class': 'resultWrapper'})
"""
'''