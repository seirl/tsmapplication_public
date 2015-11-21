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
from AccountingData import AccountingData
import Config
from Settings import load_settings

# PyQt5
from PyQt5.QtCore import pyqtSignal, QFileSystemWatcher, QObject, QTimer

# General python modules
import logging
import os
from shutil import rmtree
import sys
from time import time


class WoWHelper(QObject):
    INVALID_VERSION = 0
    RELEASE_VERSION = 1
    BETA_VERSION = 2
    DEV_VERSION = 3


    addons_folder_changed = pyqtSignal()


    def __init__(self):
        QObject.__init__(self)
        self._watcher = QFileSystemWatcher()
        self._watcher.fileChanged.connect(self.directory_changed)
        self._watcher.directoryChanged.connect(self.directory_changed)
        # initialize instances variables
        self._accounting_data = []
        self._addons_folder_change_scheduled = False
        self._valid_wow_path = False
        self._settings = load_settings(Config.DEFAULT_SETTINGS)

        # load the WoW path
        self.set_wow_path("")
        if not self.set_wow_path(self._settings.wow_path):
            # try to automatically determine the wow path
            self.find_wow_path()


    def _get_addon_path(self, addon=None):
        if not addon:
            return os.path.abspath(os.path.join(self._settings.wow_path, "Interface", "Addons"))
        else:
            return os.path.abspath(os.path.join(self._settings.wow_path, "Interface", "Addons", addon))


    def _addons_folder_changed_delayed(self):
        self._addons_folder_change_scheduled = False
        self.addons_folder_changed.emit()


    def find_wow_path(self):
        if sys.platform.startswith("win32"):
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
        elif sys.platform.startswith("darwin"):
            search_paths = [os.path.join("~/Applications", "World of Warcraft")]
        else:
            logging.getLogger().error("Unsupported platform ({})".format(sys.platform))
            return
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
        # update the accounting info
        self._accounting_data = {}
        wtf_accounts_path = os.path.abspath(os.path.join(self._settings.wow_path, "WTF", "Account"))
        for account_name in os.listdir(wtf_accounts_path):
            sv_path = os.path.abspath(os.path.join(wtf_accounts_path, account_name, "SavedVariables", "TradeSkillMaster_Accounting.lua"))
            if os.path.isfile(sv_path):
                self._accounting_data[account_name] = AccountingData(sv_path)
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
        return AppData(os.path.join(self._get_addon_path("TradeSkillMaster_AppHelper"), "AppData.lua"))


    def get_accounting_accounts(self):
        return list(self._accounting_data.keys())


    def get_accounting_data_object(self, account):
        return self._accounting_data[account]
