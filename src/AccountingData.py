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


# PyQt5
from PyQt5.QtCore import QStandardPaths


class AccountingData:
    SALES_DATA = 0
    PURCHASES_DATA = 1
    INCOME_DATA = 2
    EXPENSES_DATA = 3
    EXPIRED_DATA = 4
    CANCELED_DATA = 5


    def __init__(self, path):
        self._path = path


    def _lua_file_get(self, path, *target_scope):
        current_scope = []
        with open(path, encoding="utf8") as f:
            for line in f:
                if "--" in line:
                    # remove the comment
                    line = line[:line.find("--")]
                # remove all whitespace
                line = line.strip()
                if line.endswith("= {"):
                    # entering a new level of scope
                    if line.startswith("["):
                        # they key is within brackets and quotes
                        current_scope.append(line[line.find("[")+2:line.rfind("]")-1])
                    else:
                        # this key is not within brackets or quotes
                        current_scope.append(line[:line.find("=")].strip())
                elif line.endswith("},") or line.endswith("}"):
                    # go up a level of scope
                    print(current_scope)
                    current_scope.pop()
                else:
                    # this is data within the current scope
                    pass


    def get_realms(self):
        realms = []
        # self._lua_file_get(self._path)
        with open(self._path, encoding="utf8") as f:
            in_scope = 0
            for line in f:
                line = line.rstrip()
                if in_scope == 0 and line == "\t[\"_scopeKeys\"] = {":
                    in_scope = 1
                elif in_scope == 1 and line == "\t\t[\"realm\"] = {":
                    in_scope = 2
                elif in_scope == 2:
                    if line == "\t\t},":
                        # we're done
                        break
                    realms.append(line[line.find("\"")+1:line.rfind("\"")])
        return realms


    def export(self, *args):
        valid_types = [attr for attr in dir(self) if not callable(attr) and not attr.startswith("__")]
        for data_type in args:
            assert(data in valid_types)
        print("HERE2", QStandardPaths.writableLocation(QStandardPaths.DesktopLocation))
