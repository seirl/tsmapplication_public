# This file is part of the TSM Desktop Application.
#
# The TSM Desktop Application is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The TSM Desktop Application is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the TSM Desktop Application.  If not, see <http://www.gnu.org/licenses/>.


import logging
import os
from time import time


class SavedVariables:
    def __init__(self, path, addon):
        self._path = path
        self._data = None
        self._timestamp = 0
        self._db_name = addon + "DB"


    def _parse_token(self, token):
        if not token or token.isspace():
            return None
        elif token == "true":
            return True
        elif token == "false":
            return False
        elif token.isdigit():
            return int(token)
        else:
            return token


    def _token_iterator(self, data):
        escaped = False
        is_comment = False
        in_string = None
        current_token = ""

        for c in data:
            if not in_string and c == "-":
                is_comment += 1
            elif (is_comment == 1 and c != "-") or c == "\n":
                is_comment = 0
            if is_comment >= 2:
                pass
            elif in_string:
                # we only care about escaping the quotes - all other escape characters will be preserved
                if c == in_string and not escaped:
                    # this is the end of the string
                    yield current_token
                    in_string = None
                    current_token = ""
                elif c == "\\" and not escaped:
                    # this is an escape character
                    escaped = True
                    current_token += c
                else:
                    escaped = False
                    current_token += c
            elif c == "-":
                is_comment = 1
            elif c.isspace():
                # whitespace can separate tokens
                yield self._parse_token(current_token)
                current_token = ""
            elif c in ["'", "\""]:
                in_string = c
            elif c in ["{", "}", "[", "]", ",", "="]:
                # these characters are tokens and separators
                yield self._parse_token(current_token)
                current_token = c
                yield self._parse_token(current_token)
                current_token = ""
            else:
                # this is a character of some token
                current_token += c
        assert(not in_string)
        # insert the last token if necessary
        yield self._parse_token(current_token)


    def _update_data(self):
        self._data = None
        if not os.path.isfile(self._path):
            return
        with open(self._path, encoding="utf8", errors="replace") as f:
            data = f.read()
        if not data:
            return
        numeric_index = 1
        result = {}
        scope = []
        numeric_index_stack = []
        def insert_result(key, value):
            temp = result
            for s in scope:
                temp = temp[s]
            temp[key] = value
        tokenizer = iter([x for x in self._token_iterator(data) if x is not None])
        while True:
            try:
                token = next(tokenizer)
            except StopIteration:
                break
            if not scope:
                # this must be the variable name
                key = token
                # next token is '='
                assert(next(tokenizer) == '=')
                # next token is the value
                value = next(tokenizer)
                if value == "{":
                    # the value is a table
                    insert_result(key, {})
                    scope.append(key)
                    numeric_index_stack.append(numeric_index)
                    numeric_index = 1
                elif value != "nil":
                    # this is a regular element
                    insert_result(key, value)
            elif token == "[":
                # next token is the key
                token = next(tokenizer)
                key = token
                # next token is the the ']' followed by the '='
                assert(next(tokenizer) == ']')
                assert(next(tokenizer) == '=')
                # next token is the value
                value = next(tokenizer)
                if value == "{":
                    # the value is a table
                    insert_result(key, {})
                    scope.append(key)
                    numeric_index_stack.append(numeric_index)
                    numeric_index = 1
                else:
                    # this is a regular element
                    insert_result(key, value)
            elif token == ",":
                # this is a separator
                pass
            elif token == "{":
                # entering a new scope as a numerically indexed inner-table
                insert_result(numeric_index, {})
                scope.append(numeric_index)
                numeric_index_stack.append(numeric_index)
                numeric_index = 1
            elif token == "}":
                # leaving the current scope
                scope.pop()
                numeric_index = numeric_index_stack.pop() + 1
            else:
                # this is a numerically indexed element in the table
                insert_result(numeric_index, token)
                numeric_index += 1
        assert(not scope)
        if self._db_name in result:
            self._data = result[self._db_name]


    def get_data(self):
        if not os.path.isfile(self._path):
            self._data = None
        else:
            modified_time = int(os.path.getmtime(self._path))
            if modified_time > self._timestamp:
                try:
                    self._update_data()
                except:
                    logging.getLogger().error("Failed to parse file: {}".format(self._path))
                    self._data = None
        return self._data
