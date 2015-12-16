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


class AppData:
    TYPES = ["AUCTIONDB_MARKET_DATA", "SHOPPING_SEARCHES", "WOWUCTION_MARKET_DATA", "APP_INFO"]


    def __init__(self, path):
        self._path = path
        self._info = []
        self._modified = False
        try:
            with open(self._path, encoding="utf8") as app_data_file:
                for line in app_data_file:
                    line = line.strip()
                    data = line[:line.rfind("--")-1]
                    try:
                        type, realm, time = line[line.rfind("--")+3:-1].split(",")
                    except ValueError:
                        continue
                    if type in self.TYPES:
                        self._info.append({'data': data, 'type': type, 'realm': realm, 'time': int(time)})
        except:
            pass


    def _get_info(self, type, realm):
        for info in self._info:
            if info['type'] == type and info['realm'] == realm:
                return info
        return None


    def last_update(self, type, realm):
        assert(type in self.TYPES)
        info = self._get_info(type, realm)
        if not info:
            return 0
        return info['time']


    def update(self, type, realm, data, time, store_raw=False):
        self._modified = True
        assert(type in self.TYPES)
        info = self._get_info(type, realm)
        if not info:
            info = {'data': None, 'type': type, 'realm': realm, 'time': 0}
            self._info.append(info)
        info['time'] = time
        if store_raw:
            info['data'] = 'select(2, ...).LoadData("{}","{}",{})'.format(type, realm, data)
        else:
            info['data'] = 'select(2, ...).LoadData("{}","{}",[[return {}]])'.format(type, realm, data)


    def save(self):
        if not self._modified:
            return
        with open(self._path, 'w', encoding="utf8") as app_data_file:
            for info in self._info:
                app_data_file.write("{} --<{},{},{}>\n".format(info['data'], info['type'], info['realm'], info['time']))
