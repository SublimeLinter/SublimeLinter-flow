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
    version_args = 'version'
    version_re = r'(?P<version>\d+\.\d+\.\d+)'
    version_requirement = '>= 0.17.0'
    tempfile_suffix = '-'  # Flow only works on files on disk

    regex = r'''(?xim)
        # Match file path
        ^(?P<file>.*)\:.*$\r?\n
        # First error line
        ^(?P<padding_1>\s*(?P<line_1>[0-9]+)\:\s)(?:.*)$\r?\n
        ^(?:(?P<offset_1>\s*)(?P<code_1>\^+)\s*)(?P<error_1>.*)$\r?\n
        # Optional second message - function call
        (?:
            ^(?P<padding_2>\s*(?P<line_2>[0-9]+)\:\s)(?:.*)$\r?\n
            ^(?:(?P<offset_2>\s*)(?P<code_2>\^+)\s*)(?:
                # Messages can reference code in other files, so we need to account for that
                (?P<error_small_2>.*)\sSee\:\s(?P<reference_2>.*)|
                (?P<error_2>.*)
            )$\r?\n
        )?
        # Optional third message - reference to definition
        (?:
            ^(?P<padding_3>\s*(?P<line_3>[0-9]+)\:\s)(?:.*)$\r?\n
            ^(?:(?P<offset_3>\s*)(?P<code_3>\^+)\s*)(?:
                # Messages can reference code in other files, so we need to account for that
                (?P<error_small_3>.*)\sSee\:\s(?P<reference_3>.*)|
                (?P<error_3>.*)
            )$\r?\n
        )?
    '''

    multiline = True
    defaults = {
        # Allows the user to lint *all* files, regardless of whether they have the `/* @flow */` declaration at the top.
        'all': False,

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

        if merged_settings['all']:
            command.append('--all')

        command.append('--color=never')

        return command

    def split_match(self, match):
        """
        Return the components of the match.

        We override this to catch linter error messages and return better
        error messages.
        """

        def err(g):
            return match.group('error_small_%d' % g) or match.group('error_%d' % g)

        def ref(g1, g2):
            return match.group('reference_%d' % g1) or match.group('reference_%d' % g2)

        def msg(error1, error2, reference=None):
            if reference:
                return '%s %s, See: %s' % (error1, error2, reference)
            else:
                return '%s %s' % (error1, error2)

        if match:
            open_file_name = os.path.basename(self.view.file_name())
            if match.group('file') == open_file_name:

                # Flow displays errors between 1 and 3 lines depending on the type of error
                # We reconstruct the error message depending on the number of lines
                if match.group('line_3'):
                    message = msg(err(2), err(3), ref(2, 3))
                    if match.group('reference_3'):
                        target = 2
                    else:
                        target = 3
                else:
                    if match.group('line_2'):
                        message = msg(match.group('error_1'), err(2), match.group('reference_2'))
                    else:
                        message = match.group('error_1')
                    target = 1
                line_start = int(match.group('line_%d' % target))
                col_start = len(match.group('offset_%d' % target)) - len(match.group('padding_%d' % target))
                near = ' ' * len(match.group('code_%d' % target))
                line_start = line_start - 1

                print(line_start, col_start, near, '|', message)

                # match, line, col, error, warning, message, near
                return match, line_start, col_start, True, False, message, near

        return match, None, None, None, None, '', None
