import itertools
import multiprocessing as mp
import os
import time

from Config import Config
from BaseExecutor import BaseExecutor
from ProxyService import ProxyService

class CommandTemplate:
    def __init__(self, template, *var_generators, nested=False):
        self.template = template
        self.var_generators = var_generators
        self.nested = nested

    def build(self):
        var_combinations = itertools.product(*self.var_generators)
        if self.nested:  # flatten the stream via itertools.chain.from_iterable
            var_combinations = map(itertools.chain.from_iterable, var_combinations)
        commands = itertools.starmap(self.template, var_combinations)
        commands = tuple(commands)
        return commands

class CommandEnhancer:
    def __init__(self, initializer, decorator):
        self.initializer = initializer
        self.decorator = decorator

class EnhancedExecutor(BaseExecutor):
    def __init__(self, command_template, command_enhancer, workers=1):
        self.commands = command_template.build()
        self.command_enhancer = command_enhancer
        self.workers = workers

    def run_commands_split(self, command, mp_dict):
        pid = os.getpid()
        if mp_dict.get(pid) is None:
            mp_dict[pid] = self.command_enhancer.initializer()
        for i in range(Config.max_attempts):
            enhanced_command = self.command_enhancer.decorator(command, mp_dict[pid])
            print(f">> Running [{pid}] attempt#[{i}] with processes [{enhanced_command}].")
            output = self.run_command(enhanced_command)
            if output.get('returncode', None) == 0:
                break
            print(f"** Command failed. Reinitializing mp cache...")
            mp_dict[pid] = self.command_enhancer.initializer()
        print(f"<< Finished [{pid}] attempt#{i}/{Config.max_attempts} with processes [{enhanced_command}].")
        return output

    def run_commands_on_workers(self):
        start_time = time.time()
        with mp.Pool(processes=self.workers) as pool, mp.Manager() as manager:
            mp_dict = manager.dict()
            print(f">> Multiprocessing pool {(self.workers, pool, mp_dict)} loaded.")
            starargs = ((command, mp_dict) for command in self.commands)
            results = pool.starmap(self.run_commands_split, starargs)
            print(f"<< Multiprocessing pool {(self.workers, pool, mp_dict)} unloaded.")
        print(f"Duration on workers = {time.time() - start_time}")
        return results


if __name__ == '__main__':
    proxy_service = ProxyService()
    initializer = proxy_service.generate_proxy
    def decorator(c, p):  # multiprocessing hates lambdas
        return f"{c} --proxy {p}" if p is not None else c
    curl_proxy_decorator = CommandEnhancer(initializer, decorator)

    echo_template = lambda a, b: f"echo {a} {b}"
    echo_vars_1 = [1, 2, 3]
    echo_vars_2 = [4, 5, 6]
    command_template = CommandTemplate(echo_template, echo_vars_1, echo_vars_2)

    test_workers = 3
    enhancedExecutor = EnhancedExecutor(command_template, curl_proxy_decorator, test_workers)
    results = enhancedExecutor.run_commands_on_workers()
    print(f"Results = {results}\nSuccesses: {sum([r['returncode'] == 0 for r in results])}/{len(results)}")
