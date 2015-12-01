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
from AppData import AppData
import Config
from SavedVariables import SavedVariables
from Settings import load_settings

# PyQt5
from PyQt5.QtCore import pyqtSignal, QFileSystemWatcher, QObject, QStandardPaths, QTimer

# General python modules
from datetime import datetime, timedelta
import logging
import os
from shutil import rmtree
from time import time
from zipfile import ZipFile, ZIP_LZMA


class WoWHelper(QObject):
    INVALID_VERSION = 0
    RELEASE_VERSION = 1
    BETA_VERSION = 2
    DEV_VERSION = 3


    addons_folder_changed = pyqtSignal()


    def __init__(self):
        QObject.__init__(self)
        self._watcher = QFileSystemWatcher()
        self._watcher.directoryChanged.connect(self.directory_changed)
        # initialize instances variables
        self._addons_folder_change_scheduled = False
        self._valid_wow_path = False
        self._addons = []
        self._settings = load_settings(Config.DEFAULT_SETTINGS)
        self._saved_variables = {}

        # load the WoW path
        if not self.set_wow_path(self._settings.wow_path):
            # try to automatically determine the wow path
            self.find_wow_path()


    def _get_addon_path(self, addon=None):
        if addon:
            return os.path.abspath(os.path.join(self._settings.wow_path, "Interface", "Addons", addon))
        else:
            return os.path.abspath(os.path.join(self._settings.wow_path, "Interface", "Addons"))


    def _get_saved_variables_path(self, account, addon=None):
        if addon:
            return os.path.join(self._settings.wow_path, "WTF", "Account", account, "SavedVariables", "{}.lua".format(addon))
        else:
            return os.path.join(self._settings.wow_path, "WTF", "Account", account, "SavedVariables")


    def _get_saved_variables(self, account, addon):
        if (account, addon) not in self._saved_variables:
            self._saved_variables[(account, addon)] = SavedVariables(self._get_saved_variables_path(account, addon), addon)
        return self._saved_variables[(account, addon)].get_data()


    def _get_backup_path(self):
        backup_path = os.path.join(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation), "Backups")
        if not os.path.exists(backup_path):
            os.makedirs(backup_path)
        return backup_path


    def get_accounts(self):
        accounts = []
        if not os.path.isdir(os.path.join(self._settings.wow_path, "WTF", "Account")):
            return accounts
        for account_name in os.listdir(os.path.join(self._settings.wow_path, "WTF", "Account")):
            if os.path.isfile(self._get_saved_variables_path(account_name, "TradeSkillMaster")):
                accounts.append(account_name)
        return accounts


    def _addons_folder_changed_delayed(self):
        self._addons_folder_change_scheduled = False
        self.addons_folder_changed.emit()


    def find_wow_path(self):
        if Config.IS_WINDOWS:
            import string
            from ctypes import windll

            search_paths = []
            bitmask = windll.kernel32.GetLogicalDrives()
            for drive in ["{}:\\".format(c) for i, c in enumerate(string.ascii_uppercase) if bitmask & (1 << i)]:
                try:
                    if windll.kernel32.GetDriveTypeW(drive) == 3: # magic number for the "fixed" drive type
                        for sub_path in ["", "Games", "Program Files", "Program Files (x86)"]:
                            search_paths.append(os.path.join(drive, sub_path, "World of Warcraft"))
                except Exception as e:
                    logging.getLogger().error("Could not lookup drive type for '{}' ({})".format(drive, str(e)))
        elif Config.IS_MAC:
            search_paths = [os.path.join("~/Applications", "World of Warcraft")]
        else:
            raise Exception("Unexpected platform")
        for path in search_paths:
            if self.set_wow_path(path):
                return


    def directory_changed(self, path):
        if path == self._get_addon_path():
            if not self._addons_folder_change_scheduled:
                self._addons_folder_change_scheduled = True
                QTimer.singleShot(5000, self._addons_folder_changed_delayed)


    def set_wow_path(self, path):
        # We'll validate the WoW folder by checking for Interface/Addons and WTF folders
        if not os.path.isdir(os.path.abspath(os.path.join(path, "Interface", "Addons"))) or not os.path.isdir(os.path.abspath(os.path.join(path, "WTF"))):
            if self._settings.wow_path != "":
                self._watcher.removePath(self._get_addon_path())
            self._settings.wow_path = ""
            self._valid_wow_path = False
            return False
        self._valid_wow_path = True
        # store the new path
        prev_wow_path = self._settings.wow_path
        self._settings.wow_path = os.path.abspath(path)
        logging.getLogger().info("WoW path is set to '{}'".format(self._settings.wow_path))
        # update the directory watcher
        if prev_wow_path != "":
            self._watcher.removePath(self._get_addon_path())
        self._watcher.addPath(self._get_addon_path())
        return True


    def has_valid_wow_path(self):
        return self._valid_wow_path


    def get_installed_version(self, addon):
        if self._settings.wow_path == "":
            return self.INVALID_VERSION, 0, ""
        # look at the addon's TOC file to get the current version
        toc_path = os.path.abspath(os.path.join(self._get_addon_path(addon), "{}.toc".format(addon)))
        if not os.path.isfile(toc_path):
            return self.INVALID_VERSION, 0, ""
        # get the version as a string
        version_str = None
        with open(toc_path) as toc_file:
            for line in toc_file:
                if "## Version:" in line:
                    version_str = line[len("## Version:"):].strip()
        if not version_str:
            return self.INVALID_VERSION, 0, ""
        elif version_str == "@project-version@":
            # this is a dev version
            return self.DEV_VERSION, -1, "Dev"
        elif version_str[1] == "X":
            # this is a beta version
            parts = version_str.split("X")
            if len(parts) != 2 or not all(x.isdigit() for x in parts):
                logging.getLogger().error("Invalid version line for {}: {}".format(addon, line))
                return self.INVALID_VERSION, 0, ""
            return self.BETA_VERSION, int(parts[0]) * 1000 + int(parts[1]), version_str
        elif version_str[0] == "v":
            # this is a release version
            parts = version_str[1:].split(".")
            # check that the parts are all numeric
            if not all(x.isdigit() for x in parts):
                logging.getLogger().error("Invalid version line for {}: {}".format(addon, line))
                return self.INVALID_VERSION, 0, ""
            if len(parts) == 2:
                return self.RELEASE_VERSION, int(parts[0]) * 10000 + int(parts[1]) * 100, version_str
            elif len(parts) == 3:
                return self.RELEASE_VERSION, int(parts[0]) * 10000 + int(parts[1]) * 100 + int(parts[2]), version_str
        else:
            logging.getLogger().error("Invalid version line for {}: {}".format(addon, line))
        return self.INVALID_VERSION, 0, ""


    def delete_addon(self, addon):
        assert(addon)
        addon_dir = self._get_addon_path(addon)
        if os.path.isdir(addon_dir):
            rmtree(addon_dir)


    def install_addon(self, addon, zip):
        # remove the addon if it already exists
        self.delete_addon(addon)
        zip.extractall(self._get_addon_path())


    def get_app_data(self):
        path = os.path.join(self._get_addon_path("TradeSkillMaster_AppHelper"), "AppData.lua")
        if not os.path.isfile(path):
            return None
        return AppData(path)


    def get_accounting_accounts(self):
        result = {}
        for account_name in self.get_accounts():
            data = self._get_saved_variables(account_name, "TradeSkillMaster_Accounting")
            if data:
                try:
                    result[account_name] = [x for x in data['_scopeKeys']['realm'].values()]
                except KeyError:
                    pass
        return result


    def export_accounting_csv(self, account, realm, key):
        DB_KEYS = {
            'sales': "csvSales",
            'purchases': "csvBuys",
            'income': "csvIncome",
            'expenses': "csvExpense",
            'expired': "csvExpired",
            'canceled': "csvCancelled"
        }
        path = os.path.join(QStandardPaths.writableLocation(QStandardPaths.DesktopLocation), "Accounting_{}_{}.csv".format(realm, key))
        try:
            data = self._get_saved_variables(account, "TradeSkillMaster_Accounting")
            if not data:
                return
            data = data["r@{}@{}".format(realm, DB_KEYS[key])]
        except KeyError as e:
            logging.getLogger().error("Failed to export accounting data ({}, {}, {}): {}".format(account, realm, key, str(e)))
            return
        if type(data) != str:
            logging.getLogger().error("Failed to export accounting data ({}, {}, {})".format(account, realm, key))
            return
        data = data.replace("\\n", "\n")
        with open(path, 'w', encoding="utf8") as f:
            f.write(data)
        logging.getLogger().info("Exported accounting data to {}".format(path))


    def set_addons_and_do_backups(self, addons):
        self._addons = addons
        return self._do_backup()


    def _saved_variables_iterator(self, account):
        for addon in self._addons:
            sv_path = self._get_saved_variables_path(account, addon)
            if os.path.isfile(sv_path):
                yield sv_path


    def _backup_file_iterator(self, target_account=None):
        for file_path in os.listdir(self._get_backup_path()):
            file_name = os.path.basename(file_path)
            if file_name.endswith(".zip") and file_name.count(Config.BACKUP_NAME_SEPARATOR) == 1:
                # this is probably a backup .zip
                account, timestamp = file_name[:-4].split(Config.BACKUP_NAME_SEPARATOR)
                if target_account and account != target_account:
                    continue
                try:
                    timestamp = datetime.strptime(timestamp, Config.BACKUP_TIME_FORMAT)
                except ValueError:
                    continue
                yield account, timestamp, file_path


    def _do_backup(self, account=None):
        accounts = [account] if account else self.get_accounts()
        backup_path = self._get_backup_path()
        backed_up = []
        for account_name in accounts:
            # delete expired backups first so we'll do a new backup if the most recent one expired
            backup_times = []
            for _, timestamp, path in self._backup_file_iterator(account_name):
                if (datetime.now() - timestamp) > timedelta(seconds=self._settings.backup_expire):
                    logging.getLogger().info("Purged old backup for account ({}): {}".format(account_name, path))
                    os.remove(path)
                else:
                    backup_times.append(timestamp)

            # check if the files have changed since the last backup - if not, don't take a new backup
            modified_times = [int(os.path.getmtime(sv_path)) for sv_path in self._saved_variables_iterator(account_name)]
            if not modified_times:
                logging.getLogger().info("No files to back-up for account ({})".format(account_name))
                continue
            elif backup_times:
                last_backup = max(backup_times)
                if datetime.fromtimestamp(max(modified_times)) < last_backup:
                    logging.getLogger().info("No update since last backup for account ({})".format(account_name))
                    continue
                elif (datetime.now() - last_backup) < timedelta(seconds=self._settings.backup_period):
                    logging.getLogger().info("Backup period hasn't yet passed for account ({})".format(account_name))
                    continue

            # do the backup
            assert(Config.BACKUP_NAME_SEPARATOR not in Config.BACKUP_TIME_FORMAT)
            assert(Config.BACKUP_NAME_SEPARATOR not in account_name)
            zip_name = "{}_{}.zip".format(account_name, datetime.now().strftime(Config.BACKUP_TIME_FORMAT))
            with ZipFile(os.path.join(backup_path, zip_name), 'w', ZIP_LZMA) as zip:
                for sv_path in self._saved_variables_iterator(account_name):
                    zip.write(sv_path, os.path.basename(sv_path))
            backed_up.append(account_name)
            logging.getLogger().info("Created backup for account ({})".format(account_name))
        return backed_up


    def get_backups(self):
        return [{'account': account, 'timestamp':timestamp} for account, timestamp, _ in self._backup_file_iterator()]


    def restore_backup(self, account, timestamp):
        self._do_backup(account)
        backup_path = self._get_backup_path()
        zip_path = os.path.abspath(os.path.join(backup_path, "{}_{}.zip".format(account, timestamp)))
        if not os.path.isfile(zip_path):
            logging.getLogger().error("Could not find backup: {}".format(zip_path))
            return False
        with ZipFile(zip_path) as zip:
            zip.extractall(self._get_saved_variables_path(account))
        logging.getLogger().info("Restored backup ({}, {})".format(account, timestamp))
        return True


    def get_black_market_data(self):
        result = {}
        for account in self.get_accounts():
            data = self._get_saved_variables(account, "TradeSkillMaster_AppHelper")
            if not data:
                continue
            try:
                account_data = data["blackMarket"]
                region = data["region"]
                if not account_data or not region:
                    continue
            except KeyError as e:
                logging.getLogger().warn("No black market data for {}".format(account))
                continue
            for realm, data in account_data.items():
                if data['updateTime'] < (int(time()) - Config.MAX_BLACK_MARKET_AGE):
                    # data is too old to bother uploading
                    continue
                key = (region, realm)
                if key not in result or result[key]['updateTime'] < data['updateTime']:
                    result[key] = data
        return result


    def _parse_csv(self, data):
        import csv
        result = []
        rows = [x for x in csv.reader(data.split('\\n'), delimiter=',')]
        if len(rows) <= 1:
            return None
        keys = rows.pop(0)
        for row in rows:
            if len(row) != len(keys):
                # invalid row
                return None
            result_row = {}
            for i, cell_value in enumerate(row):
                result_row[keys[i]] = cell_value
            result.append(result_row)
        return result


    def get_accounting_data(self):
        result = {}
        for account in self.get_accounts():
            app_helper_data = self._get_saved_variables(account, "TradeSkillMaster_AppHelper")
            if not app_helper_data:
                continue
            region = app_helper_data['region'] if 'region' in app_helper_data else None
            if not region:
                continue
            data = self._get_saved_variables(account, "TradeSkillMaster_Accounting")
            for realm in data['_scopeKeys']['realm'].values():
                def parse_data_helper(key):
                    if key not in data:
                        return None
                    parsed_data = self._parse_csv(data[key])
                    if not parsed_data:
                        return None
                    return [x for x in parsed_data if 'source' in x and x['source'] == "Auction"]
                sales = parse_data_helper("r@{}@csvSales".format(realm))
                buys = parse_data_helper("r@{}@csvBuys".format(realm))
                def parse_save_time_helper(key):
                    if key not in data:
                        return None
                    return [int(x) for x in data[key].split(",") if x.isdigit()]
                save_time_sales = parse_save_time_helper("r@{}@saveTimeSales".format(realm))
                save_time_buys = parse_save_time_helper("r@{}@saveTimeBuys".format(realm))
                account_data = {'data': {}, 'updateTime': 0}
                def process_data_iterator(data, save_times):
                    if not data or not save_times or len(data) != len(save_times):
                        return
                    for i, record in enumerate(data):
                        item_string_parts = record['itemString'].split(":")
                        if item_string_parts[0] == "i":
                            yield int(item_string_parts[1]), int(record['price']), int(record['stackSize']), int(record['quantity']), int(record['time']), int(save_times[i])
                for item_id, price, stack_size, quantity, sale_time, save_time in process_data_iterator(sales, save_time_sales):
                    if item_id not in account_data['data']:
                        account_data['data'][item_id] = []
                    account_data['data'][item_id].append([price, stack_size, quantity, sale_time, save_time, 2])
                    account_data['updateTime'] = max(account_data['updateTime'], save_time)
                for item_id, price, stack_size, quantity, sale_time, save_time in process_data_iterator(buys, save_time_buys):
                    if item_id not in account_data['data']:
                        account_data['data'][item_id] = []
                    account_data['data'][item_id].append([price, stack_size, quantity, sale_time, save_time, 3])
                    account_data['updateTime'] = max(account_data['updateTime'], save_time)
                if account_data:
                    result[(region, realm, account)] = account_data
        return result


    def get_group_data(self):
        result = {}
        for account in self.get_accounts():
            account_data = {}
            data = self._get_saved_variables(account, "TradeSkillMaster_AppHelper")
            if not data:
                continue
            try:
                account_data = data["shoppingMaxPrices"]
                region = data["region"]
                if not account_data or not region:
                    continue
            except KeyError as e:
                logging.getLogger().warn("No shopping data for {}".format(account))
                continue
            for profile, data in account_data.items():
                data = data.copy()
                update_time = data.pop('updateTime', None)
                if update_time:
                    account_data[profile] = {'updateTime': update_time, 'data': data}
            for profile, data in account_data.items():
                data['profiles'] = list(account_data.keys())
                result[(account, profile)] = data
        return result
