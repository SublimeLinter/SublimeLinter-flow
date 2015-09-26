#
# linter.py
# Linter for SublimeLinter3, a code checking framework for Sublime Text 3
#
# Written by Clifton Kaznocha
# Copyright (c) 2014 Clifton Kaznocha
#
# License: MIT
#

"""This module exports the Flow plugin class."""

import os
import sublime
from SublimeLinter.lint import Linter


class Flow(Linter):

    """Provides an interface to flow."""

    syntax = ('javascript', 'html', 'javascriptnext', 'javascript (babel)', 'javascript (jsx)', 'jsx')
    executable = 'flow'
    version_args = '--version'
    version_re = r'(?P<version>\d+\.\d+\.\d+)'
    version_requirement = '>= 0.1.0'
    regex = r'''(?xi)
        # Warning location and optional title for the message
        ^.+/(?P<file_name>[^/]+\.(js|html|jsx)):(?P<line>\d+):(?P<col>\d+),((?P<another_line>\d+):)?(?P<col_end>\d+):\s*(?P<message_title>.+)$\r?\n

        # Main lint message
        ^(?P<message>.+)$

        # Optional message, only extract the text, leave the path
        (\r?\n\s?\s?/.+:\s(?P<message_footer>.+)(?=\r?\n$))?
    '''
    multiline = True
    defaults = {
        # Allows the user to lint *all* files, regardless of whether they have the `/* @flow */` declaration at the top.
        'all': False,

        # Allow to bypass the 50 errors cap
        'show-all-errors': True,

        # Allows flow to start server (makes things faster on larger projects)
        'use-server': True,

        # Options for flow
        '--lib:,': ''
    }
    word_re = r'^((\'|")?[^"\']+(\'|")?)(?=[\s\,\)\]])'
    selectors = {
        'html': 'source.js.embedded.html'
    }

    def cmd(self):
        """Return the command line to execute."""
        command = [self.executable_path]

        if self.get_merged_settings()['use-server']:
            command.append('--no-auto-start')
        else:
            command.append('check')

        if self.get_merged_settings()['show-all-errors']:
            command.append('--show-all-errors')

        if self.get_merged_settings()['all']:
            command.append('--all')

        return command

    def split_match(self, match):
        """
        Return the components of the match.

        We override this to catch linter error messages and return better
        error messages.
        """

        if match:
            open_file_name = os.path.basename(self.view.file_name())
            linted_file_name = match.group('file_name')

            if linted_file_name == open_file_name:
                message_title = match.group('message_title')
                message = match.group('message')
                message_footer = match.group('message_footer') or ""

                if message_title and message_title.strip():
                    message = '"{0}"" {1} {2}'.format(
                        message_title,
                        message,
                        message_footer
                    )

                line = max(int(match.group('line')) - 1, 0)
                col = int(match.group('col')) - 1
                another_line = int(match.group('another_line') or line)
                col_end = int(match.group('col_end'))
                near_start_point = self.view.text_point(line, col)
                near_end_point = self.view.text_point(another_line, col_end)
                near = self.view.substr(sublime.Region(near_start_point, near_end_point))

                # match, line, col, error, warning, message, near
                return match, line, col, True, False, message, near

        return match, None, None, None, None, '', None
