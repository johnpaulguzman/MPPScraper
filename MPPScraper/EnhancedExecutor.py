import multiprocessing_utils
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.proxy import Proxy, ProxyType

import itertools
import multiprocessing as mp
import time

from Config import Config
from ProxyService import ProxyService


thread_local = multiprocessing_utils.local()

class CommandContext:
    def __init__(self, initialize, get_context, execution_plan):
        self.initialize = initialize
        self.get_context = get_context
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
        driver = self.command_context.get_context()
        for i in range(Config.max_attempts):
            output = self.command_context.execution_plan(driver, arg)
            if output.get('succeeded', False):
                break
            print(f"** Command failed. Running with a new context...")
            driver = self.command_context.initialize()
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

proxy_service = ProxyService()

def initialize_driver():
    global thread_local
    desired_capabilities = webdriver.DesiredCapabilities.CHROME
    proxy = Proxy()
    proxy.proxy_type = ProxyType.MANUAL
    proxy.http_proxy = proxy.ssl_proxy = proxy_service.generate_proxy()
    proxy.add_to_capabilities(desired_capabilities)
    chrome_options = Options()
    #chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(desired_capabilities=desired_capabilities, options=chrome_options)
    setattr(thread_local, 'driver', driver)
    return driver

def get_driver():
    driver = getattr(thread_local, 'driver', None)
    if driver is None:
        driver = initialize_driver()
    return driver

def driver_execution(driver, url):
    driver.get(url)
    WebDriverWait(driver, 60).until(lambda d: d.execute_script('return document.readyState') == 'complete') 
    time.sleep(10)
    currency = driver.find_element_by_css_selector('a#XZ_N-dropdown').text

    # Inspect element + https://www.w3schools.com/cssref/css_selectors.asp
    import code; code.interact(local={**locals(), **globals()}) ## INTERACT

    tickets = driver.find_elements_by_css_selector('div.resultWrapper')
    ticket = tickets[0]
    segments = ticket.find_elements_by_css_selector('div.segment-row')
    segment = segments[0]
    date = segment.find_element_by_css_selector('div.date').text
    time = segment.find_element_by_css_selector('div.segmentTimes').text
    cabin_class = segment.find_element_by_css_selector('span.segmentCabinClass').text
    duration = segment.find_element_by_css_selector('span.segmentDuration').text
    codes = segment.find_element_by_css_selector('div.airport-codes').text
    plane = segment.find_element_by_css_selector('div.planeDetails').text

    output = str(results)
    succeedeed = True
    
    return { 'output': output, 'succeeded': succeedeed }
    
command_context = CommandContext(initialize_driver, get_driver, driver_execution)

###########################################################

def url_template(a): return f"{a}"
url_vars = ['https://www.kayak.com/flights/JAX-SIN/2020-02-28/2020-03-12/1adults/children-1S-1L?sort=price_a', 'https://www.kayak.com/flights/JAX-SIN/2020-02-28/2020-03-22/1adults/children-1S-1L?sort=price_a']

arg_template = CommandTemplate(url_template, url_vars)

###########################################################

workers = 2
context_executor = ContextExecutor(arg_template, command_context, workers)
results = context_executor.run_commands_on_workers()
print(f"Results = {results}\nSuccesses: {sum([r['returncode'] == 0 for r in results])}/{len(results)}")
import code; code.interact(local={**locals(), **globals()}) ## INTERACT
