import multiprocessing_utils as mpu

from Config import Config

import itertools
import logging
import multiprocessing as mp
import random
import time


logger = logging.getLogger(__name__)

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
    def __init__(self, command_context, arg_template, workers=1):
        self.command_context = command_context
        self.args = arg_template.build()
        self.workers = workers

    def get_or_create_cache(self):
        cache = getattr(CommandContext.thread_local, 'cache', None)
        if cache is None:
            logger.debug("Creating new cache.")
            cache = self.command_context.create_cache()
            setattr(CommandContext.thread_local, 'cache', cache)
        return cache

    def repopulate_cache(self):
        cache = getattr(CommandContext.thread_local, 'cache', None)
        if cache is not None:
            logger.debug("Deleting old cache.")
            self.command_context.destroy_cache(cache)
        logger.debug("Repopulating cache.")
        cache = self.command_context.create_cache()
        setattr(CommandContext.thread_local, 'cache', cache)
        return cache

    def destroy_cache(self, _):
        cache = getattr(CommandContext.thread_local, 'cache', None)
        if cache is not None:
            logger.debug("Destroying cache.")
            self.command_context.destroy_cache(cache)

    def run_commands_split(self, arg):
        cache = self.get_or_create_cache()
        for i in range(1, Config.max_attempts + 1):
            logger.info(f"Running attempt #({i}/{Config.max_attempts}) with processes [{arg}].")
            output = self.command_context.execution_plan(cache, arg)
            if output is not None:
                break
            logger.error(f"Command failed; retrying with a new context cache.")
            cache = self.repopulate_cache()
        else:
            output = []
        logger.info(f"Finished with attempt #({i}/{Config.max_attempts}) with processes [{arg}].")
        return output

    def run_commands_on_workers(self):
        ### self.run_commands_split(self.args.__iter__().__next__()) # # # # # # ALLOW INTERACTIVE # # # # # #
        start_time = time.time()
        with mp.Pool(processes=self.workers) as pool:
            logger.info(f"Loaded multiprocessing pool {(self.workers, pool)}.")
            nested_results = pool.map(self.run_commands_split, self.args)
            logger.info(f"Unloaded multiprocessing pool {(self.workers, pool)}.")
            pool.map(self.destroy_cache, (None, ) * self.workers)
        logger.info(f"Duration on workers = {(time.time() - start_time):.6}.")
        results = list(itertools.chain.from_iterable(nested_results))
        return results


if __name__ == '__main__':
    from LogFormatter import LogFormatter
    logger = LogFormatter.configure_root_logger()
    
    def test_create_cache(): return "my_cache"
    def test_destroy_cache(cache): return None
    def test_execution_plan(cache, args): return [f"execution of {cache} / {args}"]
    test_command_context = CommandContext(test_create_cache, test_destroy_cache, test_execution_plan)

    def test_templ(x, y): return f"some_command {x} {y}"
    test_gen_x = [1, 2, 3]
    test_gen_y = [4, 5, 6]
    test_command_templ = CommandTemplate(test_templ, test_gen_x, test_gen_y)

    workers = 3
    test_context_executor = ContextExecutor(test_command_context, test_command_templ, workers)
    results = test_context_executor.run_commands_on_workers()
    print(f"Results: {results}")
    assert all(results) and len(results) == len(test_gen_x) * len(test_gen_y)
