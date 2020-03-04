import multiprocessing_utils as mpu
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options

import itertools
import multiprocessing as mp
import random
import time
import json
import os

from Config import Config
from ProxyService import ProxyService


class CommandContext:
    thread_local = mpu.local()

    def __init__(self, create_cache, destroy_cache, execution_plan):
        self.create_cache = create_cache
        self.destroy_cache = destroy_cache
        self.execution_plan = execution_plan

class CommandTemplate:
    def __init__(self, template, *var_generators, nested=False, limit=None):
        self.template = template
        self.var_generators = var_generators
        self.nested = nested
        self.limit = limit

    def build(self):
        var_combinations = itertools.product(*self.var_generators)
        if self.nested:  # flatten the stream via itertools.chain.from_iterable
            var_combinations = map(itertools.chain.from_iterable, var_combinations)
        args = itertools.starmap(self.template, var_combinations)
        if self.limit is not None:
            args = random.choices(list(args), k=self.limit)
        return args

class ContextExecutor():
    def __init__(self, arg_template, command_context, workers=1):
        self.args = arg_template.build()
        self.command_context = command_context
        self.workers = workers

    def get_or_create_cache(self):
        cache = getattr(CommandContext.thread_local, 'cache', None)
        if cache is None:
            cache = self.command_context.create_cache()
            setattr(CommandContext.thread_local, 'cache', cache)
        return cache

    def repopulate_cache(self):
        cache = self.get_or_create_cache()
        self.command_context.destroy_cache(cache)
        cache = self.command_context.create_cache()
        setattr(CommandContext.thread_local, 'cache', cache)
        return cache

    def run_commands_split(self, arg):
        cache = self.get_or_create_cache()
        for i in range(1, Config.max_attempts + 1):
            print(f"<< Running attempt#{i}/{Config.max_attempts} with processes [{arg}].")
            output = self.command_context.execution_plan(cache, arg)
            if output is not None:
                break
            print(f"** Command failed. Running with a new context cache ...")
            cache = self.repopulate_cache()
        print(f"<< Finished attempt#{i}/{Config.max_attempts} with processes [{arg}].")
        return output

    def run_commands_on_workers(self):
        # self.run_commands_split(self.args.__iter__().__next__()) # # # # # # ALLOW INTERACTIVE # # # # # #
        start_time = time.time()
        with mp.Pool(processes=self.workers) as pool:
            print(f">> Multiprocessing pool {(self.workers, pool)} loaded.")
            nested_results = pool.map(self.run_commands_split, self.args)
            print(f"<< Multiprocessing pool {(self.workers, pool)} unloaded.")
        print(f"Duration on workers = {time.time() - start_time}")
        results = list(itertools.chain.from_iterable(nested_results))
        return results

###########################################################
###########################################################
###########################################################

def get_process_idx():
    raw_idx = mp.current_process()._identity
    if raw_idx is None or raw_idx == tuple():
        return 0
    return raw_idx[0] - 1

def create_driver():
    options = Options()
    # options.add_argument('--headless')
    if Config.use_proxy:
        idx = get_process_idx()
        proxy = ProxyService.generate_proxy(idx=idx)
        options.add_argument(f'--proxy-server={proxy}')
    driver = webdriver.Chrome(options=options)
    return driver

def delete_driver(driver):
    driver.quit()

def wait_page_loading(driver):
    WebDriverWait(driver, 60).until(lambda d: d.execute_script('return document.readyState') == 'complete')
    time.sleep(30)  # probably unnecessary

def check_detected_as_bot(driver):
    if "/bots." in driver.current_url or "/bots/" in driver.current_url:
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

def driver_execution_plan(driver, url):
    try:
        # driver.get("http://ifconfig.me")
        driver.get(url)
        for REDUNDANT_CODE in range(2):  # ?????????????????????????????????????????????????????????????????????
            check_detected_as_bot(driver)
            wait_page_loading(driver)
            click_popups(driver)
        ticket_details = extract_ticket_details(driver)
        return ticket_details
    except Exception as e:
        print(f"Exception in driver: {e}")
        driver.quit()
        return None

command_context = CommandContext(create_driver, delete_driver, driver_execution_plan)

###########################################################

def tuple_stats(name, generator, peek=2):
    tup = tuple(generator)
    print(f">> {name} = {tup[ :peek]}, ... {tup[-peek: ]}\n   length = {len(tup)}\n")
    return tup

code_csv = pd.read_csv("airport_codes.csv")
code_range = code_csv['Code'].to_list()
code_combinations = ((c1, c2) for c1 in code_range for c2 in code_range if c1 != c2)

(range_days, range_weeks, range_months) = (0, 0, 1)
date_start = pd.to_datetime('today')
date_end = date_start + pd.DateOffset(days=range_days, weeks=range_weeks, months=range_months)
date_range = pd.date_range(date_start, date_end)
roundtrip_combinations = ((str(d1.date()), str(d2.date())) for d1 in date_range for d2 in date_range if d1 < d2)
oneway_combinations = ((str(d.date()), None) for d in date_range)
date_combinations = itertools.chain(oneway_combinations, roundtrip_combinations)

cabin_class_combinations = (('economy', ), ('premium', ), ('business', ), ('first', ))

max_adults = 9
max_children = 7
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
                                (lap_infant + seat_infant + child + youth) <= max_children and \
                                lap_infant <= (adult + senior))

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

codes_templ = lambda code_origin, code_destination: f"{code_origin}-{code_destination}"
dates_templ = lambda date_departure, date_return: f"{date_departure}" if date_return is None else f"{date_departure}/{date_return}"
children_templ = lambda lap_infants, seat_infants, children, youth: "" if (lap_infants + seat_infants + children + youth) == 0 else f"children{'-1S' * seat_infants}{'-1L' * lap_infants}{'-11' * children}{'-17' * youth}"
travellers_templ = lambda adults, seniors, lap_infants, seat_infants, children, youth: f"{adults}adults/{seniors}seniors/{children_templ(lap_infants, seat_infants, children, youth)}"
bags_templ = lambda carryon_bags, checked_bags: f"fs=cfc={carryon_bags};bfc={checked_bags}"
def search_templ(code_origin, code_destination, date_departure, date_return, cabin_class, adults, seniors, \
        lap_infants, seat_infants, children, youth, carryon_bags, checked_bags, sort='price_a'):
    """ Sample format: https://www.kayak.com/flights/MNL-SYD/2020-03-19/2020-03-26/business/1adults/1seniors/children-1S-1L-1L-11-17?fs=cfc=1;bfc=2&sort=price_a """
    codes = codes_templ(code_origin, code_destination)
    dates = dates_templ(date_departure, date_return)
    travellers = travellers_templ(adults, seniors, lap_infants, seat_infants, children, youth)
    bags = bags_templ(carryon_bags, checked_bags)
    return f"https://www.kayak.com/flights/{codes}/{dates}/{cabin_class}/{travellers}?{bags}&sort={sort}"

# """ Filter possible combinations
code_combinations = filter(lambda cc: cc[0] == 'MNL', code_combinations)
date_combinations = filter(lambda dc: True, date_combinations)
cabin_class_combinations = filter(lambda ccc: ccc == ('economy', ), cabin_class_combinations)
travellers_combinations = filter(lambda tc: tc == (1, 0, 0, 0, 0, 0), travellers_combinations)
bags_combinations = filter(lambda bags: bags == (0, 0), bags_combinations)
# """
nested = True
limit = 4  # 9
command_templ = CommandTemplate(search_templ, code_combinations, date_combinations, cabin_class_combinations, travellers_combinations, bags_combinations, nested=nested, limit=limit)

workers = 2  # 3
context_executor = ContextExecutor(command_templ, command_context, workers)
results = context_executor.run_commands_on_workers()

out_path = os.path.join(Config.data_path, "kayak_dump.json")
with open(out_path, 'w', encoding='utf-8') as out_file:
    json.dump(results, out_file, indent=4)
    print(f"Results written to: {out_path}")

# 4 on 2 workers ~ 960 sec due to bot detections

import code; code.interact(local={**locals(), **globals()}) ## INTERACT

