import shlex
import subprocess as sp
import time

from Config import Config

class BaseExecutor:
    def run_command(self, command):
        print(f">> Running: {command}")
        process = sp.Popen(shlex.split(command), stdout=sp.PIPE, stderr=sp.PIPE)
        start_time = time.time()
        (out, err, rc, duration) = (*process.communicate(), process.returncode, time.time() - start_time)
        time.sleep(Config.timeout)
        result = {'command': command, 'stdout': out, 'stderr': err, 'returncode': rc, 'duration': duration}
        print(f">> Finished: {command}")
        return result

    def decode_result(self, result):
        return result['stdout'].decode('utf-8')

    def get_output(self, command):
        result = self.run_command(command)
        output = self.decode_result(result)
        return output


if __name__ == '__main__':
    baseExecutor = BaseExecutor()
    baseExecutor.run_command("echo Hello")
    print(baseExecutor.get_output("echo World!"))
