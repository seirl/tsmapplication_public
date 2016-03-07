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


# Local modules
import Config
from Settings import load_settings

# General python modules
from datetime import datetime
import re


class Backup:
    def __init__(self, zip_name):
        self._settings = load_settings(Config.DEFAULT_SETTINGS)
        if not zip_name.endswith(".zip"):
            raise ValueError("Invalid zip name")
        elif zip_name.count(Config.BACKUP_NAME_SEPARATOR) == 1:
            self.is_remote = False
            self.system_id = self._settings.system_id
            self.account, self.timestamp = zip_name[:-4].split(Config.BACKUP_NAME_SEPARATOR)
        elif zip_name.count(Config.BACKUP_NAME_SEPARATOR) == 2:
            self.is_remote = True
            self.system_id, self.account, self.timestamp = zip_name[:-4].split(Config.BACKUP_NAME_SEPARATOR)
        else:
            raise ValueError("Invalid account")
        self.timestamp = datetime.strptime(self.timestamp, Config.BACKUP_TIME_FORMAT)
        if re.match("[^a-zA-Z0-9#]", self.account):
            raise ValueError("Invalid account")

    def get_zip_name(self):
        if self.is_remote:
            return self.get_remote_zip_name()
        else:
            return self.get_local_zip_name()

    def get_local_zip_name(self):
        return Config.BACKUP_NAME_SEPARATOR.join([self.account, self.timestamp.strftime(Config.BACKUP_TIME_FORMAT)]) + ".zip"

    def get_remote_zip_name(self):
        return Config.BACKUP_NAME_SEPARATOR.join([self.system_id, self.account, self.timestamp.strftime(Config.BACKUP_TIME_FORMAT)]) + ".zip"
