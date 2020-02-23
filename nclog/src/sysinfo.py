"""
    ***********************************************************************************************
    * INTEL CORPORATION CONFIDENTIAL Copyright(c) 2017-2020 Intel Corporation. All Rights Reserved.
    *
    * The source code contained or described herein and all documents related to the
    * source code ("Material") are owned by Intel Corporation or its suppliers or
    * licensors. Title to the Material remains with Intel Corporation or its suppliers
    * and licensors. The Material contains trade secrets and proprietary and
    * confidential information of Intel or its suppliers and licensors. The Material
    * is protected by worldwide copyright and trade secret laws and treaty provisions.
    * No part of the Material may be used, copied, reproduced, modified, published,
    * uploaded, posted, transmitted, distributed, or disclosed in any way without
    * Intel's prior express written permission.
    *
    * No license under any patent, copyright, trade secret or other intellectual
    * property right is granted to or conferred upon you by disclosure or delivery of
    * the Materials, either expressly, by implication, inducement, estoppel or
    * otherwise. Any license under such intellectual property rights must be express
    * and approved by Intel in writing.
     **********************************************************************************************
"""

import os
import sys
import traceback
import commands

import utils
import logging

LOGFILE = '/tmp/sysinfo.log'
logging.basicConfig(filename=LOGFILE, filemode='a',
                    format='%(asctime)s [%(levelname)s] %(module)s: %(message)s', datefmt='%Y/%d/%m %H:%M:%S',
                    level=logging.DEBUG)
logger = logging.getLogger('sysinfo')


_FILES_LOG_BEFORE_ITER = [
    "/proc/schedstat",
    "/proc/buddyinfo",
    "/proc/meminfo",
    "/proc/slabinfo",
    "/proc/interrupts"
]

_LOG_PER_BOOT = [
    "lspci -vvnn", "gcc --version",
    "uptime", "dmidecode", "ifconfig -a", "brctl show", "ip link",
    "ld --version", "mount", "hostname",
    "numactl --hardware show", "lscpu", "fdisk -l",
    "whoami", "printenv", "python -V"
]

_FILES_LOG_PER_BOOT = [
    "/proc/cpuinfo", "/proc/modules", "/proc/interrupts", "/proc/partitions",
    "/sys/kernel/debug/sched_features",
    "/proc/pci", "/proc/meminfo", "/proc/version",
    "/sys/devices/system/clocksource/clocksource0/current_clocksource",
    "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
]

_DEFAULT_FILES_TO_LOG_AFTER_ITERATION = [
    "/proc/buddyinfo",
    "/proc/schedstat", "/proc/meminfo",
    "/proc/slabinfo", "/proc/interrupts"
]


def ignore_errors(msg):
    """ decorator for wrapping """
    def decorator(fn):
        def decorated_func(*args, **dargs):
            try:
                fn(*args, **dargs)
            except Exception:
                logger.error(msg)
                traceback.print_exc(file=sys.stdout)
        return decorated_func
    return decorator


class sysinfo(object):
    """
    Sysinfo Class
    """
    def __init__(self, res_dir):
        self.sys_dir = self._get_sysdir(res_dir)
        self._messages_size = None
        self._messages_inode = None

        self.loggab = set()
        self.boot_log = set()
        for cmd in _LOG_PER_BOOT:
            self.boot_log.add(utils.command(cmd))
        for filename in _FILES_LOG_PER_BOOT:
            self.boot_log.add(utils.logfile(filename))

        self.before_iter_log = set()
        for fname in _FILES_LOG_BEFORE_ITER:
            self.before_iter_log.add(
                utils.logfile(fname, log=os.path.basename(fname) + '.before'))

        self.after_iter_log = set()
        for fname in _DEFAULT_FILES_TO_LOG_AFTER_ITERATION:
            self.after_iter_log.add(
                utils.logfile(fname, log=os.path.basename(fname) + '.after'))

        self.loggab.add(utils.command("df -mP", log="df"))

        self.loggab.add(utils.command("dmesg -c", log="dmesg", compress=True))
        self.loggab.add(utils.command("cat /tmp/sph.log", log="sph_log", compress=True))
        self.loggab.add(utils.command("ls  /dev/disk/by-id", log="usb_disk"))

        self.boot_log.add(utils.logfile("/proc/cmdline", keyval=True))

        self.boot_log.add(utils.logfile('/sys/class/dmi/id/bios_version', log='bios_version'))
        self.boot_log.add(utils.logfile('/etc/issue', log='host_version'))

        self.boot_log.add(utils.logfile('/proc/mounts', log='proc_mounts'))
        self.boot_log.add(utils.command("uname -a", log="uname", keyval=True))

    @staticmethod
    def _get_sysdir(res_dir):
        sys_dir = os.path.join(res_dir, "sysinfo")
        if not os.path.exists(sys_dir):
            os.makedirs(sys_dir)
        return sys_dir

    @ignore_errors("log_after sysinfo error:")
    def log_after(self, logdir):
        """
        Pst collect log
        :param logdir:
        """
        logger.info("Starting collection ...")
        test_sysinfodir = self._get_sysdir(logdir)

        for log in (self.loggab | self.boot_log):
            log.run(test_sysinfodir)

        # Data system log
        self._log_data(test_sysinfodir)

    @ignore_errors("log_before sysinfo error:")
    def log_before(self):
        """
        pre collect log
        """
        if os.path.exists("/var/log/messages"):
            stat = os.stat("/var/log/messages")
            self._messages_size = stat.st_size
            self._messages_inode = stat.st_ino
        elif os.path.exists("/var/log/dmesg"):
            stat = os.stat("/var/log/dmesg")
            self._messages_size = stat.st_size
            self._messages_inode = stat.st_ino

    def _log_data(self, logdir):
        """
        Log all data
        :param logdir:
        """
        try:
            paths = ["/var/log/messages", "/var/log/dmesg", "/var/log/syslog", "/tmp/sph.log"]
            for lpath in paths:
                if os.path.exists(lpath):
                    break
            else:
                raise RuntimeError("file not found  {}".format(lpath))

            skip = 0
            if hasattr(self, "_messages_size"):
                current_inode = os.stat(lpath).st_ino
                if current_inode == self._messages_inode:
                    skip = self._messages_size
            tmp_path = "/tmp/hstmessages"
            commands.getstatusoutput(utils.get_command("cat {} > {}".format(lpath, tmp_path)))
            file_messages = open(os.path.join(logdir, os.path.basename(lpath)), 'w')
            data_messages = open(tmp_path)
            try:
                data_messages.seek(skip)
                while True:
                    in_data = data_messages.read(200000)
                    if not in_data:
                        break
                    file_messages.write(in_data)
            finally:
                file_messages.close()
                data_messages.close()
        except ValueError as ex:
            logger.error(ex)
        except Exception as ex:
            logger.error("System log failed: {}".format(ex))
