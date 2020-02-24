"""
    ***********************************************************************************************
    * Copyright (c) 2017-2020, Intel Corporation.
    *
    * This program is free software; you can redistribute it and/or modify it
    * under the terms and conditions of the GNU General Public License,
    * version 2, as published by the Free Software Foundation.
    *
    * This program is distributed in the hope it will be useful, but WITHOUT
    * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
    * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
     **********************************************************************************************
"""
import os
import time
import commands
import logging
import shutil

import utils
from os.path import expanduser


NNPIINFO_DIR = os.path.join('{}'.format(expanduser("~")), 'nclog', 'nnpi')
LOGFILE = '/tmp/nnpiinfo.log'


logging.basicConfig(filename=LOGFILE, filemode='a',
                    format='%(asctime)s [%(levelname)s] %(module)s: %(message)s', datefmt='%Y/%d/%m %H:%M:%S',
                    level=logging.DEBUG)
logger = logging.getLogger('nnpiinfo')


def check_card_connection():
    _, stdout = commands.getstatusoutput("/opt/intel_nnpi/bin/nnpi_ctl list")
    if "no such device" in stdout:
        logger.info("No devices connected to server")
        return False
    return True


def get_num_of_devs():
    _, stdout = commands.getstatusoutput("/opt/intel_nnpi/bin/nnpi_ctl list -n 2> /dev/null | grep -v '^$' | wc -l")
    return int(stdout)


class CollectRealTimeInfo(object):
    """
    Collect system and component logs
    during test runtime
    """
    def __init__(self):
        self.logh = 1
        self.activate = False
        self.realtime_logs = set()
        self.output_path = os.path.join(NNPIINFO_DIR, 'realtime')
        utils.mkdir(self.output_path)

    def collect_all_logs(self):
        """
        Collect NNPI SysLog

        """
        if not check_card_connection():
            return False
        # Collect from host
        self.realtime_logs.add(utils.command(utils.get_command("dmesg"), log="host_dmesg"))
        self.realtime_logs.add(utils.command(utils.get_command("cat /var/log/messages"), log="host_messages"))
        # Collect from card
        num_of_device = get_num_of_devs()
        for dev in range(0, num_of_device):
            with open(os.path.join(self.output_path, "sph.log_{}".format(str(dev))), 'a') as sphlog_file:
                _, stdout = commands.getstatusoutput(utils.get_command("/opt/intel_nnpi/bin/nnpi_ctl log -history {} -devices {}".format(self.logh, dev)))
                sphlog_file.write(stdout)
                if len(stdout) > 0:
                    sphlog_file.write("\n")

            with open(os.path.join(self.output_path, "messages_{}.log".format(str(dev))), 'a') as messages_file:
                _, stdout = commands.getstatusoutput(utils.get_command("/opt/intel_nnpi/bin/nnpi_ctl log -sys_history {} -devices {}".format(self.logh, dev)))
                messages_file.write(stdout)
                messages_file.write("\n")

            self.realtime_logs.add(utils.command(utils.get_command("/opt/intel_nnpi/bin/nnpi_ctl log -crash -devices {}".format(dev)), log="crash_{}.log".format(str(dev))))

        for log in self.realtime_logs:
            log.run(self.output_path)

        self.logh = self.logh + 1
        logger.info("log history: {}".format(self.logh))


class CollectNNPIInfo(object):
    """
    Collect setups versions, environment variables,

    """

    def __init__(self):
        self._log_history = 0
        self._test_name = ""
        self._start_time = None
        self._output_dir = NNPIINFO_DIR
        self._test_output_dir = None

        #self.define_env_vars()

    def set_log_history(self):
        end_time = time.time()
        duration_time = end_time - float(self._start_time)
        if duration_time <= 0:
            duration_time = 1
        self._log_history = duration_time

    def collect_perfstat(self):
        perfstat_file = os.path.join(self._test_output_dir, 'performance_state')
        if os.path.isfile(perfstat_file):
            _, stdout = commands.getstatusoutput('rm -rf {}'.format(perfstat_file))
        logger.info("collecting performance state")
        try:
            status = self.extract_nnpi_logs('nnpi_ctl', 'perfstat -a', perfstat_file) 
            if not status:
                return False
        except Exception as ex:
            raise Exception("Couldn't use nnpi_ctl perfstat: {}".format(ex))
        return True

    def save_sw_counters(self):
        sw_counters_file = os.path.join(self._test_output_dir, 'sw_counters')
        if os.path.isfile(sw_counters_file):
            _, stdout = commands.getstatusoutput('rm -rf {}'.format(sw_counters_file))
        logger.info("collecting sw_counters")
        try:
            counters_file = os.path.join(self._output_dir, 'all_counters')
            with open(counters_file, 'w') as sys_counters:
                sys_counters.write("*system.memory*")
            exits, stdout = commands.getstatusoutput(utils.get_command('/opt/intel_nnpi/bin/nnpi_query -i {} -n 10'.format(counters_file)))
            commands.getstatusoutput('rm -f {}'.format(counters_file))
            with open(sw_counters_file, 'w') as swc_file:
                swc_file.write(stdout)
            if exits != 0:
                 return False
        except Exception as ex:
            raise Exception("Couldn't use nnpi_query: {}".format(ex))

        return True

    @staticmethod
    def extract_lib_versions(libname):
        output = libname
        exits, stdout = commands.getstatusoutput('cat /sys/module/{}/version'.format(libname))
        if exits != 0:
            return ''
        output = output + ": " + stdout
        exits, stdout = commands.getstatusoutput('cat /sys/module/{}/srcversion'.format(libname))
        if exits != 0:
            return ''
        output = output + ", " + stdout + "\n"
        return output

    def collect_versions(self):
        host_file_name = os.path.join(self._test_output_dir, 'host_versions.txt')
        card_file_name = os.path.join(self._test_output_dir, 'card_versions.txt')

        _, stdout = commands.getstatusoutput('rm -rf {}'.format(host_file_name))
        with open(host_file_name, 'a') as ver_file:
            _, stdout = commands.getstatusoutput\
                ('eu-readelf -p .comment /opt/intel_nnpi/lib/libnnpi_inference.so')
            ver_file.write('{}\n'.format(stdout))
            _, stdout = commands.getstatusoutput\
                ('modinfo /opt/intel_nnpi/modules/sphdrv.ko | grep version')
            ver_file.write('\nsphdrv.ko {}\n'.format(stdout))
        exit, stdout = commands.getstatusoutput('sed -n 7,12 p {} > tmp.txt && cat tmp.txt > {} && rm -rf tmp.txt'.format(host_file_name, host_file_name))


        with open(card_file_name, 'a') as ver_file:
            try:
                exits, stdout = commands.getstatusoutput(utils.get_command('/opt/intel_nnpi/bin/nnpi_ctl list -a'))
                if exits != 0:
                    logging.error('nnpi_ctl list: ' + stdout)
                    return False
                ver_file.write(stdout)
            except Exception as ex:
                raise Exception(logging.error("Couldn't use nnpi_ctl list: {}".format(ex)))
        return True

    @staticmethod
    def define_env_vars():
        if os.environ.has_key('LD_LIBRARY_PATH'):
            os.environ["LD_LIBRARY_PATH"] = "{}:{}".format("/opt/intel_nnpi/lib/", os.environ["LD_LIBRARY_PATH"])
        else:
            os.environ["LD_LIBRARY_PATH"] = "/opt/intel_nnpi/lib/"

    def extract_nnpi_logs(self, exe, options, out_file_name):
        num_of_devs = get_num_of_devs()
        for dev in range(0, num_of_devs):
            cmd= utils.get_command('/opt/intel_nnpi/bin/{} {} -devices {}'.format(exe, options, dev))
            exits, stdout = commands.getstatusoutput(cmd)
            if exits != 0:
                logging.error('nnpi_ctl  ' + options + ': ' + stdout)
                return False
            out_file = out_file_name + "_" + str(dev)
            with open(out_file, 'w') as _file:
                _file.write(stdout)
        return True

    def collect_crash_dump(self):
        crash_output = os.path.join(self._test_output_dir, 'crash_dump')
        commands.getstatusoutput('rm -rf {}'.format(crash_output))
        logger.info("collecting crash log")
        status = self.extract_nnpi_logs('nnpi_ctl', 'log -crash', crash_output)
        if not status:
            return status
        return True

    def collect_general_logs(self):
        #   Collect card logs
        tmp_card_messages = os.path.join(self._test_output_dir, 'messages')
        tmp_card_sphlog = os.path.join(self._test_output_dir, 'sph.log')
        # clean files
        commands.getstatusoutput('rm -rf {}'.format(tmp_card_messages))
        commands.getstatusoutput('rm -rf {}'.format(tmp_card_sphlog))
        try:
            logger.info("collecting sys-history")
            status = self.extract_nnpi_logs('nnpi_ctl', 'log -sys_history {}'.format(self._log_history), tmp_card_messages)
            if not status:
                return status
            logger.info("collecting history")
            status = self.extract_nnpi_logs('nnpi_ctl', 'log -history {}'.format(self._log_history), tmp_card_sphlog)
            if not status:
                return status
        except Exception as ex:
            raise Exception(logging.error("Couldn't use nnpi_ctl log: {}".format(ex)))
        return True

    def make_tar_file(self):
        """
        Make tar file for all available logs.
        """
        import tarfile
        _output_filename = os.path.join(self._output_dir, self._test_name)
        tar = tarfile.open("{}_logs.tar.gz".format(_output_filename), "w")
        _, stdout = commands.getstatusoutput('cd {}'.format(self._test_output_dir))
        tar.add(self._test_output_dir, arcname='{}'.format(self._test_name))
        tar.close()
        _, stdout = commands.getstatusoutput('rm -r {}'.format(self._test_output_dir))

    def collect_all(self):
        """
        Collect all nnpi available info, called after a test starts.
        """
        rt_path =output_path = os.path.join(NNPIINFO_DIR, 'realtime')
        if os.path.isdir(rt_path):
            shutil.move(rt_path,self._test_output_dir)
        if not check_card_connection():
            return False
        self.set_log_history()
        logger.info("Starting nnpi-info collection ...")
        self.collect_versions()
        self.collect_general_logs()
        self.save_sw_counters()
        self.collect_perfstat()
        self.collect_crash_dump()

    def pre_test(self):
        """
        Called before a test starts.
        """
        self._start_time = time.time()
        self._test_name = "nnpi_info_{}".format(int(self._start_time)) 
        # logs dirs
        utils.mkdir(self._output_dir)
        #
        self._test_output_dir = os.path.join(self._output_dir, self._test_name)
        utils.mkdir(self._test_output_dir)
        #collect card data
        card_file_name = os.path.join(self._test_output_dir, 'card_versions.txt')
        with open(card_file_name, 'a') as ver_file:
            try:
                exits, stdout = commands.getstatusoutput(utils.get_command('/opt/intel_nnpi/bin/nnpi_ctl list -a'))
                if exits != 0:
                    logging.error('nnpi_ctl list: ' + stdout)
                    return False
                ver_file.write(stdout)
                ver_file.write("\n")
            except Exception as ex:
                raise Exception(logging.error("Couldn't use nnpi_ctl list: {}".format(ex)))
