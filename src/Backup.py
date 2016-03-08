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

# General python modules
from datetime import datetime
import re


class Backup(object):
    """
    Can construct by specifying:
     - (`zip_name`, `is_local`, `is_remote`)
     - (`system_id`, `account`, `timestamp`, `is_local`, `is_remote`)
    """
    def __init__(self, *args, **kwargs):
        assert(len(args) == 0)
        self.is_local = kwargs['is_local']
        self.is_remote = kwargs['is_remote']
        zip_name = kwargs.get('zip_name', None)
        if zip_name:
            if not zip_name.endswith(".zip"):
                raise ValueError("Invalid zip name")
            elif zip_name.count(Config.BACKUP_NAME_SEPARATOR) == 1:
                self.system_id = Config.SYSTEM_ID
                self.account, self.timestamp = zip_name[:-4].split(Config.BACKUP_NAME_SEPARATOR)
                self.timestamp = datetime.strptime(self.timestamp, Config.BACKUP_TIME_FORMAT)
            elif zip_name.count(Config.BACKUP_NAME_SEPARATOR) == 2:
                self.system_id, self.account, self.timestamp = zip_name[:-4].split(Config.BACKUP_NAME_SEPARATOR)
                self.timestamp = datetime.fromtimestamp(int(self.timestamp))
            else:
                raise ValueError("Invalid account")
        else:
            self.system_id = kwargs['system_id']
            self.account = kwargs['account']
            self.timestamp = kwargs['timestamp']
        self.keep = kwargs.get('keep', False)
        if re.match("[^a-zA-Z0-9#]", self.account):
            raise ValueError("Invalid account")

    def __eq__(self, other):
        return self.system_id == other.system_id and self.account == other.account and self.timestamp == other.timestamp

    def get_zip_name(self):
        if self.is_remote:
            return self.get_remote_zip_name()
        else:
            return self.get_local_zip_name()

    def get_local_zip_name(self):
        return Config.BACKUP_NAME_SEPARATOR.join([self.account, self.timestamp.strftime(Config.BACKUP_TIME_FORMAT)]) + ".zip"

    def get_remote_zip_name(self):
        epoch = datetime.fromtimestamp(0)
        return Config.BACKUP_NAME_SEPARATOR.join([self.system_id, self.account, str(int((self.timestamp-epoch).total_seconds()))]) + ".zip"
