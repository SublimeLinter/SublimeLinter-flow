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
from SublimeLinter.lint import Linter


class Flow(Linter):
    """Provides an interface to flow."""

    syntax = ('javascript', 'html', 'javascriptnext', 'javascript (babel)', 'javascript (jsx)', 'jsx-real')
    executable = 'flow'
    version_args = '--version'
    version_re = r'(?P<version>\d+\.\d+\.\d+)'
    version_requirement = '>= 0.17.0'
    tempfile_suffix = '-'  # Flow only works on files on disk

    regex = r'''(?xi)
        # Warning location and optional title for the message
        ^.+\/(?P<file_name_1>.+):(?P<col_1>(\d+:\d+,(\d+:)?\d+)):\s(?P<message_title>.+)?\r?\n
        # (Optional) main message
        (^(?P<message>.+))?
        # (Optional) message footer
        \r?\n
        (^.+\/(?P<file_name_2>.+):(?P<col_2>(\d+:\d+,(\d+:)?\d+)):\s(?P<message_footer>.+))?$
        \r?\n\r?\n
    '''

    multiline = True
    defaults = {
        # Allow to bypass the 50 errors cap
        'show-all-errors': True
    }
    word_re = r'^((\'|")?[^"\']+(\'|")?)(?=[\s\,\)\]])'
    selectors = {
        'html': 'source.js.embedded.html'
    }

    def cmd(self):
        """
        Return the command to execute.

        By default, with no command selected, the 'status' command executes.
        This starts the server if it is already not started. Once the server
        has started, checks are very fast.
        """
        command = [self.executable_path]
        merged_settings = self.get_merged_settings()

        if merged_settings['show-all-errors']:
            command.append('--show-all-errors')

        # Until we update the regex, will re-use the old output format
        command.append('--old-output-format')
        command.append('--color=never')

        return command

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
            linted_file_name = match.group('file_name_1') or match.group('file_name_2')

            if linted_file_name == open_file_name:

                # In the flow message format, the message ends up getting split into a few
                # pieces for better readability - we try to reconstruct these.
                message_title = match.group('message_title')
                message = match.group('message')
                message_footer = match.group('message_footer')
                col = match.group('col_1') or match.group('col_2')

                if message_title and message_title.strip():
                    message = '"{0}" {1} "{2}"'.format(
                        message_title,
                        message,
                        message_footer
                    )

                # Get the start and ending indexes of the line and column
                line_cols = col.replace(':', ',').split(',')
                line_start = max(int(line_cols[0]) - 1, 0)
                col_start = int(line_cols[1])
                col_start -= 1

                # Multi line error
                if len(line_cols) == 4:
                    line_end = max(int(line_cols[2]) - 1, 0)
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
