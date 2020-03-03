import multiprocessing_utils
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.proxy import Proxy, ProxyType

import itertools
import json
import multiprocessing as mp
import time

from Config import Config
from ProxyService import ProxyService


thread_local = multiprocessing_utils.local()

class CommandContext:
    def __init__(self, initialize, execution_plan):
        self.initialize = initialize
        self.execution_plan = execution_plan

class CommandTemplate:
    def __init__(self, template, *var_generators, nested=False):
        self.template = template
        self.var_generators = var_generators
        self.nested = nested

    def build(self):
        var_combinations = itertools.product(*self.var_generators)
        if self.nested:  # flatten the stream via itertools.chain.from_iterable
            var_combinations = map(itertools.chain.from_iterable, var_combinations)
        args = itertools.starmap(self.template, var_combinations)
        args = tuple(args)
        return args

class ContextExecutor():
    def __init__(self, arg_template, command_context, workers=1):
        self.args = arg_template.build()
        self.command_context = command_context
        self.workers = workers

    def run_commands_split(self, arg):
        for i in range(Config.max_attempts):
            output = self.command_context.execution_plan(arg)
            if output.get('succeeded', False):
                break
            print(f"** Command failed. Running with a new context...")
            self.command_context.initialize()
        print(f"<< Finished attempt#{i}/{Config.max_attempts} with processes [{arg}].")
        return output

    def run_commands_on_workers(self):
        self.run_commands_split(self.args[0]) ######
        start_time = time.time()
        with mp.Pool(processes=self.workers) as pool:
            print(f">> Multiprocessing pool {(self.workers, pool)} loaded.")
            results = pool.map(self.run_commands_split, self.args)
            print(f"<< Multiprocessing pool {(self.workers, pool)} unloaded.")
        print(f"Duration on workers = {time.time() - start_time}")
        return results

###########################################################
###########################################################
###########################################################

def initialize_driver():
    global thread_local
    old_driver = getattr(thread_local, 'driver', None)
    if old_driver is not None:
        old_driver.quit()
    desired_capabilities = webdriver.DesiredCapabilities.CHROME
    proxy = Proxy()
    proxy.proxy_type = ProxyType.MANUAL
    proxy.http_proxy = proxy.ssl_proxy = ProxyService.generate_proxy()
    proxy.add_to_capabilities(desired_capabilities)
    chrome_options = Options()
    #chrome_options.add_argument("--headless")
    new_driver = webdriver.Chrome(desired_capabilities=desired_capabilities, options=chrome_options)
    setattr(thread_local, 'driver', new_driver)
    return new_driver

def wait_page_loading(driver):
    WebDriverWait(driver, 60).until(lambda d: d.execute_script('return document.readyState') == 'complete')
    time.sleep(15)  # probably unnecessary

def check_detected_as_bot(driver):
    if driver.find_elements_by_css_selector('div#px-captcha'):
        raise Exception("Detected as bot!")

def click_popups(driver):
    popups = [popup for popup in driver.find_elements_by_css_selector('div.Common-Widgets-Dialog-Dialog') if popup.is_displayed()]
    for popup in popups:
        x_icons = [x_icon for x_icon in popup.find_elements_by_css_selector('svg.x-icon-x') if x_icon.is_displayed()]
        for x_icon in x_icons:
            x_icon.click()

def extract_segment_details(ticket):
    ticket.click()  # expand segment details section
    segments = ticket.find_elements_by_css_selector('div.segment-row')
    segment_details = [{
        'dates': segment.find_element_by_css_selector('div.date').text,
        'times': segment.find_element_by_css_selector('div.segmentTimes').text,
        'cabin_class': segment.find_element_by_css_selector('span.segmentCabinClass').text,
        'duration': segment.find_element_by_css_selector('span.segmentDuration').text,
        'codes': segment.find_element_by_css_selector('div.airport-codes').text,
        'plane': segment.find_element_by_css_selector('div.planeDetails').text,
        } for segment in segments]
    return segment_details

def extract_ticket_details(driver):
    tickets = driver.find_elements_by_css_selector('div.resultWrapper')
    ticket_details = [{
        'currency': driver.find_element_by_css_selector('a.currency-tooltip-item').get_attribute('data-cur'),
        'details': ticket.find_elements_by_css_selector('div.section.duration')[0].text,
        'price': ticket.find_element_by_css_selector('span.price').text,
        'provider': ticket.find_element_by_css_selector('span.providerName').text,
        'priceDetails': ticket.find_element_by_css_selector('div.Flights-Results-FlightPriceSection').text,
        'segments': extract_segment_details(ticket)
        } for ticket in tickets]
    return ticket_details

def driver_execution(url):
    driver = initialize_driver()
    try:
        driver.get(url)
        wait_page_loading(driver)
        check_detected_as_bot(driver)
        click_popups(driver)
        ticket_details = extract_ticket_details(driver)
        return ticket_details
    except Exception as e:
        driver.quit()
        raise e

command_context = CommandContext(initialize_driver, driver_execution)

###########################################################
# TODO WORK 

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
    return f"https://www.kayak.com/flights/{codes}/{dates}/{cabin_class}/{travellers}?{bags}&sort={sort}"

command_templ = CommandTemplate(search_templ, code_combinations, date_combinations, \
    cabin_class_combinations, travellers_combinations, bags_combinations, nested=True)
search_combinations = command_templ.build()
search_combinations = tuple_stats("search_combinations", search_combinations)

###########################################################

workers = 2
context_executor = ContextExecutor(command_templ, command_context, workers)
results = context_executor.run_commands_on_workers()
print(f"Results = {results}\nSuccesses: {sum([r['returncode'] == 0 for r in results])}/{len(results)}")
import code; code.interact(local={**locals(), **globals()}) ## INTERACT
