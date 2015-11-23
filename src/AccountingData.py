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

# General python modules
import logging
import os


_DB_KEYS = {
    'sales': "csvSales",
    'purchases': "csvBuys",
    'income': "csvIncome",
    'expenses': "csvExpense",
    'expired': "csvExpired",
    'canceled': "csvCancelled"
}


class AccountingData:
    def __init__(self, path):
        self._path = path


    def _lua_parse_value(self, value):
        value = value.rstrip(",")
        if value.startswith("\"") and value.endswith("\""):
            # remove the quotes
            return value[1:-1]
        elif value == "true":
            return True
        elif value == "false":
            return False
        elif value.isdigit():
            return int(value)


    def _lua_file_get(self, target_scope):
        current_scope = []
        data = []
        with open(self._path, encoding="utf8") as f:
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
                        assert(line.count("]") == 1)
                        current_scope.append(line[line.find("[")+2:line.rfind("]")-1])
                    else:
                        # this key is not within brackets or quotes
                        current_scope.append(line[:line.find("=")].strip())
                elif line.endswith("},") or line.endswith("}"):
                    # go up a level of scope
                    if current_scope == target_scope:
                        # we're leaving the scope we care about so we're done
                        return data
                    current_scope.pop()
                elif current_scope == target_scope:
                    # this is data within the target scope
                    if not line.startswith("["):
                        data.append(self._lua_parse_value(line))
                elif line.startswith("["):
                    # we might just be looking for a single value
                    current_scope.append(line[line.find("[")+2:line.find("]")-1])
                    if current_scope == target_scope:
                        return self._lua_parse_value(line[line.find("=")+1:].strip())
                    current_scope.pop()


    def get_realms(self):
        realms = []
        self._lua_file_get(["TradeSkillMaster_AccountingDB", "_scopeKeys", "realm"])
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


    def export(self, realm, data_type):
        path = os.path.join(QStandardPaths.writableLocation(QStandardPaths.DesktopLocation), "Accounting_{}_{}.csv".format(realm, data_type))
        data = self._lua_file_get(["TradeSkillMaster_AccountingDB", "r@{}@{}".format(realm, _DB_KEYS[data_type])])
        if type(data) != str:
            return
        data = data.replace("\\n", "\n")
        with open(path, 'w', encoding="utf8") as f:
            f.write(data)
        logging.getLogger().info("Exported accounting data to {}".format(path))
