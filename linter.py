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
import re
from SublimeLinter.lint import Linter


class Flow(Linter):

    """Provides an interface to flow."""

    syntax = ('javascript', 'html')
    executable = 'flow'
    version_args = '--version'
    version_re = r'(?P<version>\d+\.\d+\.\d+)'
    version_requirement = '>= 0.1.0'
    regex = r'''(?xi)
        # Warning location and optional title for the message
        ^.+\/(?P<file_name_1>.+):(?P<col_1>(\d+:\d+,(\d+:)?\d+)):\s(?P<message_title>.+)?\r?\n

        # (Optional) main message
        (^(?P<message>.+))?

        # (Optional) message footer
        (\r?\n\s\s.+\/(?P<file_name_2>.+):(?P<col_2>(\d+:\d+,(\d+:)?\d+)):\s(?P<message_footer>.+))?
    '''
    multiline = True
    defaults = {
        # Allows the user to lint *all* files, regardless of whether they have the `/* @flow */` declaration at the top.
        'all': False,

        # Allow to bypass the 50 errors cap
        'show-all-errors': True,

        # Lints the loaded view buffer instead of the file
        'lint-view': True,

        # Allows flow to start server (makes things faster on larger projects)
        'use-server': True,

        # TODO: Remove the parameter if deemed unececerry
        # Options for flow
        # 'lib:,': ''
    }
    word_re = r'^((\'|")?[^"\']+(\'|")?)(?=[\s\,\)\]])'
    selectors = {
        'html': 'source.js.embedded.html'
    }

    def cmd(self):
        """Return the command line to execute."""

        command = [self.executable_path]

        # Overrides 'use-server' directive if pressent
        if not self.get_merged_settings()['use-server']:
            command.append('check')
        else:
            if self.get_merged_settings()['lint-view']:
                command.append('check-contents')
            else:
                command.append('status')

        if self.get_merged_settings()['all']:
            if 'check' in command or 'status' in command:
                command.append('--all')

        # TODO: Remove the parameter if deemed unececerry.
        # if self.get_merged_settings()['lib'] and len(self.get_merged_settings()['lib']) > 0:
        #    command.append('--lib')
        #    command.append(self.get_merged_settings()['lib'])

        if self.get_merged_settings()['show-all-errors']:
            command.append('--show-all-errors')

        return command

    def run(self, cmd, code):
        """Run the linting command and return the results."""

        if self.get_merged_settings()['lint-view']:
            # check for the @flow declaration. Currently only has to be somewhere in the file.
            if self.get_merged_settings()['all'] or re.match(r'\s*\/\*\s*\@flow\s*\*\/', code):
                # Since the linter has no knowlage about files, add the filepath to
                # function with the default filepath to reflect the default function behaviour
                cmd.append(self.filename)
                result = self.communicate(cmd, code)
                return result
            else:
                return ''
        else:
            return super().run(cmd, code)

    def split_match(self, match):
        """
        Return the components of the match.

        We override this to catch linter error messages and return better
        error messages.
        """

        if match:
            open_file_name = os.path.basename(self.view.file_name())
            # Since the filename on the top row might be different than the open file if, for example,
            # something is imported from another file. Use the filename from the footer is it's available.
            linted_file_name = match.group('file_name_2') or match.group('file_name_1')

            if linted_file_name == open_file_name:

                message_title = match.group('message_title')
                message = match.group('message')
                message_footer = match.group('message_footer')
                col = match.group('col_2') or match.group('col_1')
                message_format = []

                if message_title:
                    message_format.append('[ {0} ]')
                if message:
                    message_format.append('{1}')
                if message_footer:
                    message_format.append('[ {2} ]')

                message = " ".join(message_format).format(
                    message_title,
                    message,
                    message_footer
                )

                # Get the start and ending indexes of the line and column
                line_cols = col.replace(':', ',').split(',')
                line_start = max(int(line_cols[0])-1, 0)
                col_start = int(line_cols[1])
                col_start -= 1

                # Multi line error
                if len(line_cols) == 4:
                    line_end = max(int(line_cols[2])-1, 0)
                    col_end = int(line_cols[3])
                    near = " " * (self.view.text_point(line_end, col_end) - self.view.text_point(line_start, col_start))

                # Single line error
                else:
                    col_end = int(line_cols[2])
                    # Get the length of the column section for length of error
                    near = " " * (col_end - col_start)

                # match, line, col, error, warning, message, near
                return match, line_start, col_start, True, False, message, near

        return match, None, None, None, None, '', None
