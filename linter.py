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

import json
import re
from SublimeLinter.lint import NodeLinter, persist


class Flow(NodeLinter):
    """Provides an interface to flow."""

    syntax = ('javascript', 'html', 'javascriptnext', 'javascript (babel)', 'javascript (jsx)', 'jsx-real')
    npm_name = 'flow-bin'
    version_args = 'version --json'
    version_re = r'"semver":\s*"(?P<version>\d+\.\d+\.\d+)"'
    version_requirement = '>= 0.17.0'
    tempfile_suffix = '-'  # Flow only works on files on disk

    defaults = {
        # Allow to bypass the 50 errors cap
        'show-all-errors': True
    }
    selectors = {
        'html': 'source.js.embedded.html'
    }

    __flow_near_re = '`(?P<near>[^`]+)`'

    def cmd(self):
        """
        Return the command to execute.

        By default, with no command selected, the 'status' command executes.
        This starts the server if it is already not started. Once the server
        has started, checks are very fast.
        """
        command = ['flow']
        merged_settings = self.get_merged_settings()

        if merged_settings['show-all-errors']:
            command.append('--show-all-errors')

        command.append('--json')  # need this for simpler error handling

        return self.build_cmd(command)

    def _error_to_tuple(self, error):
        """
        Map an array of flow error messages to a fake regex match tuple.

        flow returns errors like this: {message: [{<msg>},..,]} where
        <msg>:Object {
            descr: str,
            level: str,
            path: str,
            line: number,
            endline: number,
            start: number,
            end: number
        }

        Which means we can mostly avoid dealing with regex parsing since the
        flow devs have already done that for us. Thanks flow devs!
        """
        error_messages = error.get('message', [])
        match = self.filename == error_messages[0]['path']
        # TODO(nsfmc): `line_col_base` won't work b/c we avoid `split_match`'s codepath
        line = error_messages[0]['line'] - 1
        col = error_messages[0]['start'] - 1

        level = error_messages[0].get('level', False) or error.get('level', '')
        is_error = level == 'error'
        is_warning = level == 'warning'

        combined_message = " ".join([m.get('descr', '') for m in error_messages])

        near_match = re.search(self.__flow_near_re, combined_message)
        near = near_match.group('near') if near_match else None
        persist.debug('flow line: {}, col: {}, level: {}, message: {}'.format(
            line, col, level, combined_message))

        return (match, line, col, is_error, is_warning, combined_message, near)

    def find_errors(self, output):
        """
        Convert flow's json output into a set of matches SublimeLinter can process.

        I'm not sure why find_errors isn't exposed in SublimeLinter's docs, but
        this would normally attempt to parse a regex and then return a generator
        full of sanitized matches. Instead, this implementation returns a list
        of errors processed by _error_to_tuple, ready for SublimeLinter to unpack
        """
        try:
            # calling flow in a matching syntax without a `flowconfig` will cause the
            # output of flow to be an error message. catch and return []
            parsed = json.loads(output)
        except ValueError:
            persist.debug('flow {}'.format(output))
            return []

        errors = parsed.get('errors', [])

        persist.debug('flow {} errors. passed: {}'.format(len(errors), parsed.get('passed', True)))
        return map(self._error_to_tuple, errors)
