import logging
import shlex
import subprocess as sp
import time


logger = logging.getLogger(__name__)

class SubprocessExecutor:
    @staticmethod
    def run_command(command):
        logger.info(f"Running: {command}.")
        process = sp.Popen(shlex.split(command), stdout=sp.PIPE, stderr=sp.PIPE)
        start_time = time.time()
        (stdout, stderr) = map(lambda b: b.decode('utf-8', errors='ignore'), process.communicate())
        returncode = process.returncode
        duration = time.time() - start_time
        result = {'command': command, 'stdout': stdout, 'stderr': stderr, 'returncode': returncode, 'duration': duration}
        logger.info(f"Finished: {command} | returncode: {returncode} | duration: {duration:.6}.")
        return result


if __name__ == '__main__':
    from LogFormatter import LogFormatter
    logger = LogFormatter.configure_root_logger()

    result = SubprocessExecutor.run_command("echo World!")
    assert result['returncode'] == 0
