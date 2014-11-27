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

    syntax = ('javascript', 'html')
    cmd = 'flow check'
    version_args = '--version'
    version_re = r'(?P<version>\d+\.\d+\.\d+)'
    version_requirement = '>= 0.1.0'
    regex = r'''(?xi)
        # Find the line number and col
        ^/.+/(?P<file_name>.+):(?P<line>\d+):(?P<col>\d+),\d+:\s*(?P<message1>.+)$\r?\n

        # The second part of the message
        ^(?P<message2>.+)$\r?\n

        # The third part of the message
        ^\s*.*:\d+:\d+,\d+:\s*(?P<message3>.+)\s*$
    '''
    multiline = True
    word_re = r'^((\'|")?[^"\']+(\'|")?)(?=[\s\,\)\]])'
    tempfile_suffix = '-'
    selectors = {
        'html': 'source.js.embedded.html'
    }

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
                message = '"{0}"" {1} {2}'.format(
                    match.group('message1'),
                    match.group('message2'),
                    match.group('message3')
                )

                line = max(int(match.group('line')) - 1, 0)
                col = int(match.group('col')) - 1

                # match, line, col, error, warning, message, near
                return match, line, col, True, False, message, None

        return match, None, None, None, None, '', None
