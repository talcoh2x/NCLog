#!/usr/bin/env python

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
import sys
import time
import atexit

from signal import SIGTERM


STDIN= '/dev/null'
STDOUT = '/dev/null'
STDERR = '/dev/null'


class ICEDaemon(object):
    """ Daemon class. override the run() method """

    daemon_msg = "ICE Deamon started with pid: "

    def __init__(self, pid, stdin=STDIN, stdout=STDOUT, stderr=STDERR):
        self.pid = pid
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    def ice_daemonize(self):
        """
        start a program in the background.
        :return:
        """
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as ex:
            sys.stderr.write("os.fork() number: #1 failed: {} ({})\n".format(ex.errno, ex.strerror))
            sys.exit(1)

        os.chdir("/")
        os.setsid()
        os.umask(0)

        # Starting second fork for UNIX ENV
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as ex:
            sys.stderr.write("os.fork() number: #2 failed: {} ({})\n".format(ex.errno, ex.strerror))
            sys.exit(1)

        pid = str(os.getpid())

        sys.stderr.write("\n{} {}\n".format(self.daemon_msg, pid))
        sys.stderr.flush()

        if self.pid:
            file(self.pid, 'w+').write("{}\n".format(pid))

        stdin = file(self.stdin, 'r')
        stdout = file(self.stdout, 'a+')
        stderr = file(self.stderr, 'a+', 0)

        register_atexit_func(self.removepid)

        redirect_stream(stdin, sys.stdin)
        redirect_stream(stdout, sys.stdout)
        redirect_stream(stderr, sys.stderr)

    def removepid(self):
        try:
            os.remove(self.pid)
        except OSError:
            pass

    def start(self):
        """
        Start the ICEDaemon
        """
        ################################################
        # read pid to check if the daemon already runs #
        ################################################
        try:
            pf = file(self.pid, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except (IOError, SystemExit):
            pid = None

        if pid:
            # PID self.pid
            sys.stderr.write("Daemon PID already exist.\n")
            sys.exit(1)

        ########################
        # Start the ice daemon #
        self.ice_daemonize()
        self.run()

    def get_pid(self):
        """
        Get PID
        :return: pid: process ID
        """
        try:
            pidf = file(self.pid, 'r')
            pid = int(pidf.read().strip())
            pidf.close()
        except (IOError, SystemExit):
            pid = None

        return pid

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pid
        try:
            pidf = file(self.pid, 'r')
            pid = int(pidf.read().strip())
            pidf.close()
        except IOError:
            pid = None

        if not pid:
            # PID self.pid
            sys.stderr.write("Daemon PID does not exist.\n")
            return

        try:
            while True:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)

        except OSError as err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pid):
                    os.remove(self.pid)
                else:
                    print str(err)
                    sys.exit(1)

    def restart_daemon(self):
        """
        Restart the ice daemon with stop and start.
        """
        self.stop()
        self.start()

    def run(self):
        """
        override this method when.
        """


def register_atexit_func(func):
    """
    register a function to be executed upon normal program termination

    :param func:
    """
    atexit.register(func)


def redirect_stream(sys_stream, target_stream):
    """
    redirect stream

    :param sys_stream:
    :param target_stream:
    """
    os.dup2(sys_stream.fileno(), target_stream.fileno())
