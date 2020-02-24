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

import re
import os
import sys
import commands

from os.path import expanduser
NNPIINFO_DIR = os.path.join('{}'.format(expanduser("~")), 'nclog', 'nnpi')


HOST = 'host'
CARD = 'card'
DMSEG_PATTERN = "dmesg_patterns"
SW_PATTERN = "sw_patterns"


class ErrorPattern(object):
    """
    ErrorPattern
    """
    def __init__(self):
        self.pattern = ''
        self.type = ''
        self.message = ''

    def fill_pattern(self, lines):
        for i in range(0, len(lines)):
            self.type = lines[0].rstrip()
            self.pattern = lines[1].rstrip()
            self.message = lines[2].rstrip()


class Parser(object):
    """
    Log Parser
    """
    def __init__(self, test_name, sysinfo_dir):
        self.start_line = 0
        self.pattern_lines = 4
        self.test_name = test_name
        self.sysinfo_dir =sysinfo_dir
        self.card_outputs = os.path.join(NNPIINFO_DIR, self.test_name)

        self.files_dic = dict()

    def extra_logs(self, log_name, message):
        new_msg = ''
        new_msg = new_msg + '[ ' + log_name + ' ][ ' + message + ' ]'
        return new_msg

    def parse_logs(self, output_dir_path, log_file_path, log_type, patterns_file, machine):
        """
        Collect all potential errors expressions
        :param output_dir_path: path of the logs parsing output dir
        :param log_file_path: path of the log to parse
        :param patterns_file: errors/info reference file
        :param log_type: error/info log source
        :param machine: card/ host
        :return: status of the specific log after analysis.
        """
        with open(patterns_file, 'r') as infile:
            self.files_dic = dict()
            self.pattern_lines = 4
            self.start_line = 0
            all_lines = infile.readlines()
            lines_count = len(all_lines)
            while True:
                err_ptrn = ErrorPattern()
                err_ptrn.type = all_lines[self.start_line].rstrip()
                err_ptrn.pattern = all_lines[self.start_line + 1].rstrip()
                err_ptrn.message = all_lines[self.start_line + 2].rstrip()

                # create file for each pattern type
                if not err_ptrn.type in self.files_dic:
                    self.files_dic[err_ptrn.type] = '{}/{}_{}.txt'.format(output_dir_path, err_ptrn.type, machine)

                # Search for pattern in messages
                if not os.path.isfile(log_file_path):
                    return 1
                for i, line in enumerate(open(log_file_path)):
                    match = re.search(err_ptrn.pattern, line)
                    if match:
                        with open(self.files_dic[err_ptrn.type], "a") as myfile:
                            myfile.write(self.extra_logs(log_type, err_ptrn.message) + match.string)

                self.start_line += self.pattern_lines
                if self.start_line >= lines_count:
                    break

        status = 0
        if os.path.isfile(self.files_dic['BUG']):
            if not os.stat(self.files_dic['BUG']).st_size == 0:
                status = 1
        for type, file in self.files_dic.items():
            if os.path.isfile(file):
                output_file = os.path.join(NNPIINFO_DIR, self.test_name, type + "_" + machine.upper())
                with open(output_file, "a") as outfile:
                    with open(file, "r") as myfile:
                        lines = myfile.readlines()
                        outfile.writelines(lines)
                    myfile.close()
                    commands.getstatusoutput('rm -rf {}'.format(file))
                outfile.close()

        return status

    def parse_all_logs(self):
        """
        Parse all Logs
        """
        status = 0

        # host messages
        sw_patterns_path = os.path.join(sys._MEIPASS, 'data_files', SW_PATTERN)
        log_file_path = os.path.join(self.sysinfo_dir, 'sysinfo', 'messages')
        hmesg_status = self.parse_logs(self.sysinfo_dir, log_file_path, 'messages', sw_patterns_path, HOST)

        # nnpi card logs
        card_logs_list = ['sph.log_0', 'messages_0']
        for log in card_logs_list:
            log_file_path = os.path.join(self.card_outputs, log)
            card_status = self.parse_logs(self.sysinfo_dir, log_file_path, log, sw_patterns_path, CARD)

            status = hmesg_status | card_status
        return status
