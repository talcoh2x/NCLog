import os
import shutil
import platform
import subprocess


def read_one_line(filename):
    return open(filename, 'r').readline().rstrip('\n')


def open_write_close(filename, data):
    f = open(filename, 'w')
    try:
        f.write(data)
    finally:
        f.close()


def mkdir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


def get_command(cmd, env='LD_LIBRARY_PATH=/opt/intel_nnpi/lib'):
    # we check if os.getuid() is 0 if yes, User is root and 'sudo' is not required.
    if ("CentOS Linux" in platform.linux_distribution()[0]) and (os.getuid() != 0):
        cmd = " sudo " + cmd
    return "{} {}".format(env, cmd)


class syslog(object):

    def __init__(self, log, keyval):
        self.log = log
        self.keyval = keyval

    def read(self, dir):
        path = os.path.join(dir, self.log)
        if os.path.exists(path):
            return read_one_line(path)
        else:
            return ""


class command(syslog):

    def __init__(self, cmd, log=None, keyval=False, compress=False):
        if not log:
            log = cmd.replace(" ", "_")
        super(command, self).__init__(log, keyval)
        self.cmd = cmd
        self._compress = compress

    def run(self, logdir):
        env = os.environ.copy()
        if "PATH" not in env:
            env["PATH"] = "/usr/bin:/bin"
        logf_path = os.path.join(logdir, self.log)
        stdin = open(os.devnull, "r")
        stderr = open(os.devnull, "w")
        stdout = open(logf_path, "w")
        try:
            subprocess.call(self.cmd, stdin=stdin, stdout=stdout, stderr=stderr,
                            shell=True, env=env)
        finally:
            for f in (stdin, stdout, stderr):
                f.close()
            if self._compress and os.path.exists(logf_path):
                subprocess.call('gzip -f -9 "%s"' % logf_path, shell=True, env=env)


class logfile(syslog):

    def __init__(self, path, log=None, keyval=False):
        if not log:
            log = os.path.basename(path)
        super(logfile, self).__init__(log, keyval)
        self.path = path

    def run(self, logdir):
        if os.path.exists(self.path):
            try:
                shutil.copyfile(self.path, os.path.join(logdir, self.log))
            except IOError:
                print("Not logging {}".format(self.path))
