""" Note: We may need to do some modifications to avoid getting detected as bots.
    https://stackoverflow.com/questions/33225947/can-a-website-detect-when-you-are-using-selenium-with-chromedriver
    https://stackoverflow.com/questions/53039551/selenium-webdriver-modifying-navigator-webdriver-flag-to-prevent-selenium-detec
    https://stackoverflow.com/questions/55501524/how-does-recaptcha-3-know-im-using-selenium-chromedriver
    Block google adsense which could tip off google recaptcha
"""

import pandas as pd
from geopy.distance import distance
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options

from Config import Config
from ContextExecutor import CommandContext, CommandTemplate, ContextExecutor
from ProxyService import ProxyService

import itertools
import json
import multiprocessing as mp
import re
import time
import traceback


from LogFormatter import LogFormatter
logger = LogFormatter.configure_root_logger()
workers = 4
limit = 200


######################################################################################################################
## Template
######################################################################################################################
airport_data_path = "airports.csv"  # Taken from https://ourairports.com/data/
airport_types = ('large_airport', )  # Complete version: ('small_airport', 'medium_airport', 'large_airport')

airport_data = pd.read_csv(airport_data_path)
airport_data = airport_data[(airport_data.scheduled_service == 'yes') & airport_data.type.isin(airport_types)]

code_range = airport_data['iata_code'].to_list()
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

### Generate tuple stats ###
def tuple_stats(name, generator, peek=2):  # for checking array sizes
    gen_tup = tuple(generator)
    print(f"Size of {name} = {len(gen_tup)}; Elements = {gen_tup[ :peek]}, ... {gen_tup[-peek: ]}")
    return gen_tup
code_combinations = tuple_stats("code_combinations", code_combinations)
date_combinations = tuple_stats("date_combinations", date_combinations)
cabin_class_combinations = tuple_stats("cabin_class_combinations", cabin_class_combinations)
travellers_combinations = tuple_stats("travellers_combinations", travellers_combinations)
bags_combinations = tuple_stats("bags_combinations", bags_combinations)
### Generate tuple stats ###

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

### Filter possible combinations ###
code_combinations = filter(lambda cc: cc[0] == 'MNL', code_combinations)
date_combinations = filter(lambda dc: True, date_combinations)
cabin_class_combinations = filter(lambda ccc: ccc == ('economy', ), cabin_class_combinations)
travellers_combinations = filter(lambda tc: tc == (1, 0, 0, 0, 0, 0), travellers_combinations)
bags_combinations = filter(lambda bags: bags == (0, 0), bags_combinations)
### Filter possible combinations ###

nested = True
command_templ = CommandTemplate(search_templ, code_combinations, date_combinations, cabin_class_combinations, travellers_combinations, bags_combinations, nested=nested, limit=limit)


######################################################################################################################
## Context
######################################################################################################################
def get_process_idx():
    raw_idx = mp.current_process()._identity
    if raw_idx is None or raw_idx == tuple():
        return 0
    return raw_idx[0] - 1

def create_driver():
    adblock_path = "extension_1_24_4_0.crx"
    options = Options()
    options.add_extension(adblock_path)
    # options.add_argument('--headless')  # messes with the extensions
    options.add_argument('start-maximized')
    options.add_argument('--disable-blink-features')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    if Config.use_proxy:
        idx = get_process_idx()
        proxy = ProxyService.generate_proxy(idx=idx, workers=workers)
        options.add_argument(f'--proxy-server={proxy}')
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': "Object.defineProperty(navigator, 'webdriver', { get: () => undefined })"})
    driver.execute_cdp_cmd('Network.enable', {})
    return driver

def delete_driver(driver):
    driver.quit()    

def check_detected_as_bot(driver):
    if "/bots." in driver.current_url or "/bots/" in driver.current_url:
        raise Exception("Detected as bot!")

def wait_page_loading(driver):
    timeout = 100
    WebDriverWait(driver, timeout).until(lambda drvr: drvr.execute_script('return document.readyState') == 'complete')
    WebDriverWait(driver, timeout).until(lambda drvr: all([not progress_bar.is_displayed() \
        for progress_bar in driver.find_elements_by_css_selector('div.Common-Results-ProgressBar')]))

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
        'url': driver.current_url,
        'currency': driver.find_element_by_css_selector('a.currency-tooltip-item').get_attribute('data-cur'),
        'flight_details': ticket.find_elements_by_css_selector('div.section.duration')[0].text,
        'price': ticket.find_element_by_css_selector('span.price').text,
        'provider': ticket.find_element_by_css_selector('span.providerName').text,
        'price_details': ticket.find_element_by_css_selector('div.Flights-Results-FlightPriceSection').text,
        'segments': extract_segment_details(ticket)
        } for ticket in tickets]
    return ticket_details

def first(*args):
    for arg in args:
        if arg is not None:
            return arg
    return None

def airport_distance_km(code_1, code_2):
    try:
        airport_1 = airport_data[airport_data.iata_code == code_1]
        airport_2 = airport_data[airport_data.iata_code == code_2]
        coordinates_1 = (airport_1['latitude_deg'].values[0], airport_1['longitude_deg'].values[0])
        coordinates_2 = (airport_2['latitude_deg'].values[0], airport_2['longitude_deg'].values[0])
        distance_km = distance(coordinates_1, coordinates_2).km
        return distance_km
    except Exception as e:
        logger.warning(f"Exception in airport distance calculation for ({code_1}, {code_2}): {e}.")
        traceback.print_exc()
        return None

def parse_children_code(children_code):
    return {
        'lap_infants': children_code.count('1L') if children_code else 0,
        'seat_infants': children_code.count('1S') if children_code else 0,
        'children': children_code.count('11') if children_code else 0,
        'youth': children_code.count('17') if children_code else 0,
    }

def append_ticket_details(tickets):
    mode_list = lambda lst: max(set(lst), key=lst.count) if lst else None
    day_diff = lambda date_1, date_2: (pd.to_datetime(date_2) - pd.to_datetime(date_1)).days
    non_numeric_regex = re.compile("[^0-9]")
    remove_non_numeric = lambda s: non_numeric_regex.sub('', s)
    url_regex = re.compile("https://www.kayak.com/flights/(?P<code_origin>[\w]+)-(?P<code_destination>[\w]+)/" +
        "(?P<date_departure>[\d-]+)/((?P<date_return>[\d-]+)/)?(?P<cabin_class>\w+)/" +
        "(?P<adults>\d+)adults/(?P<seniors>\d+)seniors/((?P<children_code>children[1\w-]+))?" + 
        "\?fs=cfc=(?P<carryon_bags>\d+);bfc=(?P<checked_bags>\d+)(.+)")  # TODO: use redundant fields with first(...)
    for ticket in tickets:
        url_data = url_regex.match(ticket['url']).groupdict()
        flight_details = ticket['flight_details'].split("\n")
        ticket['duration'] = flight_details[0]
        ticket['code_origin'] = flight_details[1]
        ticket['code_destination'] = flight_details[3]
        ticket['distance_km'] = airport_distance_km(ticket['code_origin'], ticket['code_destination'])
        price_details = ticket['price_details'].split("\n")
        ticket['carryon_bags'] = price_details[0]
        ticket['checked_bags'] = price_details[1]
        segments = ticket['segments']
        cabin_classes = [segment['cabin_class'] for segment in segments]
        ticket['segment_count'] = len(segments)
        ticket['cabin_class'] = first(mode_list(cabin_classes), url_data['cabin_class'])
        ticket['price_value'] = float(remove_non_numeric(ticket['price']))
        ticket['date_scraped'] = pd.to_datetime('today').date().isoformat()
        ticket['date_departure'] = url_data['date_departure']
        ticket['date_return'] = url_data['date_return']
        ticket['roundtrip'] = bool(ticket['date_return'])
        ticket['days_before_departure'] = day_diff(ticket['date_scraped'], ticket['date_departure'])
        ticket['adults'] = int(url_data['adults'])
        ticket['seniors'] = int(url_data['seniors'])
        children_data = parse_children_code(url_data['children_code'])
        ticket.update(children_data)
        ticket['travellers'] = ticket['adults'] + ticket['seniors'] + ticket['youth'] + ticket['children'] + ticket['seat_infants'] + ticket['lap_infants']
    return tickets

def driver_execution_plan(driver, url):
    wait = 70
    try:
        driver.get(url)
        check_detected_as_bot(driver)
        wait_page_loading(driver)
        click_popups(driver)
        ticket_details = extract_ticket_details(driver)
        ticket_details = append_ticket_details(ticket_details)
        time.sleep(wait)
        return ticket_details
    except Exception as e:
        logger.error(f"Exception in driver: {e}.")
        traceback.print_exc()
        driver.quit()
        return None

command_context = CommandContext(create_driver, delete_driver, driver_execution_plan)


######################################################################################################################
## Executor
######################################################################################################################
context_executor = ContextExecutor(command_context, command_templ, workers)
results = context_executor.run_commands_on_workers()
dump_path = "kayak_dump.json"
with open(dump_path, 'w', encoding='utf-8') as out_file:
    json.dump(results, out_file, indent=4)
    print(f"Results written to {dump_path}")

dataset_features = ['price_value', 'cabin_class', 'code_origin', 'code_destination', 'distance_km', 'provider', 'carryon_bags', 'checked_bags', 'date_departure', 'days_before_departure', 'roundtrip', 'adults', 'seniors', 'lap_infants', 'seat_infants', 'children', 'youth', 'travellers']
dataset_path = "kayak_dataset.csv"
dataframe = pd.DataFrame.from_dict(results)
dataset = dataframe[dataset_features]
dataset.to_csv(dataset_path, index=False, encoding='utf-8')
print(f"Dataset written to {dataset_path}")
