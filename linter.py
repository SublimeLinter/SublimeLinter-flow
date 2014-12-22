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

import os, re
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
        ^.+/(?P<file_name>[^/]+\.(js|html)):(?P<line>\d+):(?P<col>\d+),\d+:\s*(?P<message_title>.+)$\r?\n

        # Main lint message
        ^(?P<message>.+)$

        # Optional message, only extract the text, leave the path
        (\r?\n\s\s/.+:\s(?P<message_footer>.+))?
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

        # Options for flow
        'lib:,': ''
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
                
        # TODO: Not tested but seemed like a good thing to add
        if self.get_merged_settings()['lib'] and len(self.get_merged_settings()['lib']) > 0:
            command.append('--lib')
            command.append(self.get_merged_settings()['lib'])

        if self.get_merged_settings()['show-all-errors']:
            command.append('--show-all-errors')

        return command

    def run(self, cmd, code):
        """Run the linting command and return the results."""
        if self.get_merged_settings()['lint-view']:
            # check for the @flow declaration. Currently only has to be somewhere in the file.
            if self.get_merged_settings()['all'] or re.match( r'\s*\/\*\s*\@flow\s*\*\/', code):
                # Since the linter has no knowlage about files, add the filepath to
                # function with the default filepath to reflect the default function behaviour
                result = self.communicate(cmd, code).replace('-:',self.filename + ":")
                return result
            else:
                return ''
        else:
            return super().run(cmd,code)

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

                # match, line, col, error, warning, message, near
                return match, line, col, True, False, message, None

        return match, None, None, None, None, '', None
