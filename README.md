NCLog
=========


About NCLog
======================
NCLog:
    nclog is a s tool to help with system logs collecting and parsing.
    It collects system info and nnpi logs from both host and card. The tool uses nnpi_ctl and nnpi_query in order to extract the needed logs from the device(s).
    The tool was written in python 2.7 and it is available as bin file too.

How To Use
======================
You can use the compiled bin file from: src/driver/host_driver/scripts/nclog/bin

To start NCLog APP::

    ./nclog start

        -   realtime: collect sph.log, messages, dmesg and crash log every 1 sec (this option is needed in case of host/card crash/stuck).
        -   systest: enabled by default. This option needed in order to collect all system info.
        -   nnpi_ctl: enabled by default. This option needed in order to collect nnpi info and logs.

To stop NCLog APP::

    ./nclog stop
        -   analyze_logs: analyze the collected logs - sph.log, messages and dmesg, only when the test is completed.


* Note: more arguments can be added according to the project requirements.

* Tool Output::
    You can find the tool output in ~/nclog directory. it contains sysinfo and nnpi output directories.
    In addition you can find tool debug logs in /tmp

Installation dependency
==========================

The simplest installation method is through "pip".  On most POSIX
systems with Python 2.7 and "pip" available, installation can be
performed with a single command::

  sudo pip install -r requirements.txt --no-index


Build NCLog
-------------------------------------
    *   from: src/driver/host_driver/scripts/nclog
    *   do: make install
