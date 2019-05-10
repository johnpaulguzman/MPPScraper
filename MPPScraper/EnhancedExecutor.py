import multiprocessing as mp

from Config import Config
from BaseExecutor import BaseExecutor
from CommandGenerator import CommandGenerator
from ProxyService import ProxyService

# Methods used in multiprocessing has to be defined in global scope (https://bugs.python.org/issue25053)
get_thread_id = lambda: getattr(mp.current_process(), 'name')

class EnhancedExecutor(BaseExecutor):
    def default_proxy_joiner(c, p):
        return f"{c} --proxy {p}"

    def __init__(self, template, replace_dict={}, workers=1, proxy_joiner=None):
        self.commandGenerator = CommandGenerator(template, replace_dict)
        self.proxyService = ProxyService()
        self.workers = workers
        self.proxy_joiner = proxy_joiner if proxy_joiner != None else EnhancedExecutor.default_proxy_joiner

    def run_commands_split(self, commands_split):
        print(f">> Running [{get_thread_id()}] with processes [{commands_split}].")
        proxy = self.proxyService.generate_proxy() if Config.use_proxy else ""
        results = []
        for command in commands_split:
            for i in range(Config.max_attempts):
                enhanced_command = self.proxy_joiner(command, proxy) if Config.use_proxy else command
                result = self.run_command(enhanced_command)
                if result.get('returncode', None) == 0:
                    results += [result]
                    break
                proxy = self.proxyService.generate_proxy() if Config.use_proxy else ""
        print(f"<< Finished [{get_thread_id()}] with processes [{commands_split}].")
        return results

    def run_commands_on_workers(self):
        with mp.Pool(processes=self.workers) as pool:
            print(f">> Multiprocessing pool [{self.workers}] loaded.")
            splitted_commands = self.commandGenerator.split_commands(self.workers)
            workers_handles = [pool.apply_async(self.run_commands_split, args=[commands_split]) for commands_split in splitted_commands]
            splitted_results = [worker.get(Config.wait_time) for worker in workers_handles]
            results = [result for results_split in splitted_results for result in results_split]
            print(f">> Multiprocessing pool [{self.workers}] unloaded.")
        return results


if __name__ == '__main__':
    test_template = "echo <OPT1> <OPT2>"
    test_replace_dict = {
        "<OPT1>": ["1", "2", 3],
        "<OPT2>": [True, False, "Tomato"], }
    test_workers = 4
    enhancedExecutor = EnhancedExecutor(test_template, test_replace_dict, test_workers)
    results = enhancedExecutor.run_commands_on_workers()
    print(f"results:{results}, size:{len(results)}")
