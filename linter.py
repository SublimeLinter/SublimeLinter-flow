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

import logging
import json
import re
from itertools import chain, repeat

from SublimeLinter.lint import NodeLinter


logger = logging.getLogger("SublimeLinter.plugin.flow")


class Flow(NodeLinter):
    """Provides an interface to flow."""

    defaults = {
        'selector': 'source.js',
        # Allow to bypass the 50 errors cap
        'show-all-errors': True
    }

    __flow_near_re = '`(?P<near>[^`]+)`'

    def run(self, cmd, code):
        """
        Flow lint code if `@flow` pragma is present.

        if not present, this method noops
        """
        _flow_comment_re = r'\@flow'

        if not re.search(_flow_comment_re, code) \
                and not self._inline_setting_bool('all'):
            logger.info("did not find @flow pragma")
            return ''

        logger.info("found flow pragma!")
        check = super().run(cmd, code)

        coverage = super().run(_build_coverage_cmd(cmd), code) \
            if self._inline_setting_bool('coverage') else '{}'

        return '[%s,%s]' % (check, coverage)

    def cmd(self):
        """
        Return the command to execute.

        By default, with no command selected, the 'status' command executes.
        This starts the server if it is already not started. Once the server
        has started, checks are very fast.
        """
        command = ['flow']
        settings = self.settings

        command.extend(['check-contents', '$file'])

        if settings['show-all-errors']:
            command.append('--show-all-errors')

        command.append('--json')  # need this for simpler error handling

        return command

    def _error_to_tuple(self, error):
        """
        Map an array of flow error messages to a fake regex match tuple.

        this is described in `flow/tsrc/flowResult.js` in the flow repo

        flow returns errors like this
        type FlowError = {
            kind: string,
            level: string,
            message: Array<FlowMessage>,
            trace: ?Array<FlowMessage>,
            operation?: FlowMessage,
            extra?: FlowExtra,
        };
        type FlowMessage = {
            descr: string,
            type: "Blame" | "Comment",
            context?: ?string,
            loc?: ?FlowLoc,
            indent?: number,
        };

        Which means we can mostly avoid dealing with regex parsing since the
        flow devs have already done that for us. Thanks flow devs!
        """
        error_messages = error.get('message', [])
        # TODO(nsfmc): `line_col_base` won't work b/c we avoid `split_match`'s
        # codepath
        operation = error.get('operation', {})
        loc = operation.get('loc') or error_messages[0].get('loc', {})

        message = self._find_matching_msg_for_file(error)
        if message is None:
            return (False, 0, 0, False, False, '', None)

        error_context = message.get('context', '')
        loc = message.get('loc')
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
        # SublimeLinter will strip quotes of `near` strings as documented in
        # http://www.sublimelinter.com/en/latest/linter_attributes.html#regex
        # In order to preserve quotes, we have to wrap strings with more
        # quotes.
        if end and line == (message_end.get('line') - 1):
            near = '"' + error_context[col:end] + '"'
        else:
            near = None

        kind = error.get('kind', False)

        level = error.get('level', False)
        error = kind if level == 'error' else False
        warning = kind if level == 'warning' else False

        combined_message = " ".join(
            [self._format_message(msg) for msg in error_messages]
        ).strip()

        logger.info('flow line: {}, col: {}, level: {}, message: {}'.format(
            line, col, level, combined_message))

        return (True, line, col, error, warning, combined_message, near)

    def _find_matching_msg_for_file(self, flow_error):
        """
        Find the first match for the current file.

        Flow errors might point to other files, and have the current file only
        deep in additional information of the top level error.

        The error format is described in `tsrc/flowResult.js` in the flow repo:

        type FlowError = {
            kind: string,
            level: string,
            message: Array<FlowMessage>,
            trace: ?Array<FlowMessage>,
            operation?: FlowMessage,
            extra?: FlowExtra,
        };
        type FlowMessage = {
            descr: string,
            type: "Blame" | "Comment",
            context?: ?string,
            loc?: ?FlowLoc,
            indent?: number,
        };
        type FlowExtra = Array<{
            message: Array<FlowMessage>,
            children: FlowExtra,
        }>
        """

        messages = chain(
            (flow_error['operation'],) if 'operation' in flow_error else (),
            flow_error['message'],
            _traverse_extra(flow_error.get('extra')),
        )

        for message in messages:
            source = message.get('loc', {}).get('source')
            if source == self.filename:
                return message

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

            if snippet is None:
                return ""

            loc = flow_message.get('loc', {})
            if loc:
                start = loc.get('start', {}).get('column', 1) - 1
                end = loc.get('end', {}).get('column', len(snippet))
                error_descr = flow_message.get('descr').strip()
                error_string = snippet[start:end]
                if (error_string != error_descr):
                    snippet = '{} ({})'.format(error_string, error_descr)
            return snippet.strip()

    def _uncovered_to_tuple(self, uncovered, uncovered_lines):
        """
        Map an array of flow coverage locations to a fake regex match tuple.

        Since flow produces JSON output, there is no need to match error
        messages against regular expressions.
        """
        match = self.filename == uncovered.get('source')
        line = uncovered['start']['line'] - 1
        col = uncovered['start']['column'] - 1
        error = False
        warning = 'coverage'

        # SublimeLinter only uses the length of `near` if we provide the column
        # That's why we can get away with a string of the right length.
        near = ' ' * (
            uncovered['end']['offset'] - uncovered['start']['offset']
        )

        message = '\u3003'  # ditto mark
        if line not in uncovered_lines:
            message = 'Code is not covered by Flow (any type)'
            uncovered_lines.add(line)

        return (match, line, col, error, warning, message, near)

    def _empty_to_tuple(self, empty, empty_lines):
        """
        Map an array of flow coverage locations to a fake regex match tuple.

        Since flow produces JSON output, there is no need to match error
        messages against regular expressions.
        """
        match = self.filename == empty.get('source')
        line = empty['start']['line'] - 1
        col = empty['start']['column'] - 1
        error = False
        warning = 'coverage'

        # SublimeLinter only uses the length of `near` if we provide the column
        # That's why we can get away with a string of the right length.
        near = ' ' * (
            empty['end']['offset'] - empty['start']['offset']
        )

        message = '\u3003'  # ditto mark
        if line not in empty_lines:
            message = 'Code is not covered by Flow (empty type)'
            empty_lines.add(line)

        return (match, line, col, error, warning, message, near)

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
            check, coverage = json.loads(output)
        except ValueError:
            logger.info('flow {}'.format(output))
            return []

        errors = check.get('errors', [])

        logger.info('flow {} errors. passed: {}'.format(
            len(errors), check.get('passed', True)
        ))

        return chain(
            map(self._error_to_tuple, errors),
            map(self._uncovered_to_tuple,
                coverage.get('expressions', {}).get('uncovered_locs', []),
                repeat(set())),
            map(self._empty_to_tuple,
                coverage.get('expressions', {}).get('empty_locs', []),
                repeat(set()))
        )

    def _inline_setting_bool(self, s):
        """Get an inline setting as a bool."""
        setting = self.settings.get(s)
        return setting and setting not in ('False', 'false', '0')


def _traverse_extra(flow_extra):
    """Yield all messages in `flow_extra.message` and `flow_extra.childre.message`."""
    if flow_extra is None:
        return

    for x in flow_extra:
        yield from x.get('message')
        yield from _traverse_extra(x.get('children'))


def _build_coverage_cmd(cmd):
    """Infer the correct `coverage` command from the `check-contents` command."""
    return cmd[:cmd.index('check-contents')] + ['coverage', '--path', '@', '--json']
