import shlex
import subprocess as sp
import time

from Config import Config

class BaseExecutor:
    def run_command(self, command):
        print(f">> Running: {command}")
        process = sp.Popen(shlex.split(command), stdout=sp.PIPE, stderr=sp.PIPE)
        start_time = time.time()
        (stdout, stderr) = map(lambda b: b.decode('utf-8', errors='ignore'), process.communicate())
        returncode = process.returncode
        duration = time.time() - start_time
        result = {'command': command, 'stdout': stdout, 'stderr': stderr, 'returncode': returncode, 'duration': duration}
        print(f">> Finished: {command} | returncode: {returncode} | duration: {duration}")
        time.sleep(Config.timeout)
        return result


if __name__ == '__main__':
    baseExecutor = BaseExecutor()
    baseExecutor.run_command("echo Hello")
