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

    defaults = {
        # Allow to bypass the 50 errors cap
        'show-all-errors': True
    }
    selectors = {
        'html': 'source.js.embedded.html'
    }

    __flow_near_re = '`(?P<near>[^`]+)`'

    def run(self, cmd, code):
        """
        Flow lint code if `@flow` pragma is present.

        if not present, this method noops
        """
        _flow_comment_re = r'\@flow'
        if re.search(_flow_comment_re, code):
            persist.debug("found flow pragma!")
            return super().run(cmd, code)
        else:
            persist.debug("did not find @flow pragma")
            return ''

    def cmd(self):
        """
        Return the command to execute.

        By default, with no command selected, the 'status' command executes.
        This starts the server if it is already not started. Once the server
        has started, checks are very fast.
        """
        command = ['flow']
        merged_settings = self.get_merged_settings()

        command.extend(['check-contents', '@'])

        if merged_settings['show-all-errors']:
            command.append('--show-all-errors')

        command.append('--json')  # need this for simpler error handling

        c = self.build_cmd(command)
        persist.debug('flow attempting to run from: {}'.format(c))
        return c

    def _error_to_tuple(self, error):
        """
        Map an array of flow error messages to a fake regex match tuple.

        this is described in `flow/tsrc/flowResult.js` in the flow repo

        flow returns errors like this
        type FlowError = {
            message: Array<FlowMessage>,
            operation?: FlowMessage
        }
        type FlowMessage = {
            descr: string,
            type: "Blame" | "Comment",
            context?: ?string,
            loc?: ?FlowLoc,
            indent?: number,
        }

        Which means we can mostly avoid dealing with regex parsing since the
        flow devs have already done that for us. Thanks flow devs!
        """
        error_messages = error.get('message', [])
        # TODO(nsfmc): `line_col_base` won't work b/c we avoid `split_match`'s codepath
        operation = error.get('operation', {})
        loc = operation.get('loc') or error_messages[0].get('loc', {})

        error_context = operation.get('context') or error_messages[0].get('context', '')
        match = self.filename == loc.get('source')
        message_start = loc.get('start', {})
        message_end = loc.get('end', {})

        line = message_start.get('line', None)
        if line:
            line -= 1
        col = message_start.get('column', None)
        if col:
            col -= 1
        end = message_end.get('column', None)

        # slice the error message from the context and loc positions
        # If error spans multiple lines, though, don't highlight them all
        # but highlight the 1st error character by passing None as near
        if end and line == (message_end.get('line') - 1):
            near = error_context[col:end]
        else:
            near = None

        level = error.get('level', False)
        is_error = level == 'error'
        is_warning = level == 'warning'

        combined_message = " ".join([self._format_message(msg) for msg in error_messages]).strip()

        persist.debug('flow line: {}, col: {}, level: {}, message: {}'.format(
            line, col, level, combined_message))

        return (match, line, col, is_error, is_warning, combined_message, near)

    def _format_message(self, flow_message):
        """
        Format sequences of error messages depending on their type.

        comments typically contains text linking text describing the
        type of error violation

        blame messages are typically code snippets with a `descr` that
        identifies the failing error type and a loc that identifies the
        snippet that triggered the error (would typically be underlined
        with ^^^^^^ in terminal invocations)

        if possible, will try to reduce the context message (which may
        already be highlighted by the linter) to the `parameter (Type)`
        so that status bar messages will read like

            foo (String) This type is incompatible with expectedFoo (Number)
        """
        msg_type = flow_message.get('type')

        if msg_type == 'Comment':
            return flow_message.get('descr', '').strip()
        if msg_type == 'Blame':
            snippet = flow_message.get('context', '')
            loc = flow_message.get('loc', {})
            if loc:
                start = loc.get('start', {}).get('column', 1) - 1
                end = loc.get('end', {}).get('column', len(snippet))
                error_descr = flow_message.get('descr').strip()
                error_string = snippet[start:end]
                if (error_string != error_descr):
                    snippet = '{} ({})'.format(error_string, error_descr)
            return snippet.strip()

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
