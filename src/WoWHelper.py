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
from Settings import load_settings

# PyQt5
from PyQt5.QtCore import pyqtSignal, QFileSystemWatcher, QObject, QTimer

# General python modules
import logging
import os
from shutil import rmtree
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
        self._addons_folder_change_scheduled = False
        self._valid_wow_path = False
        self._settings = load_settings(Config.DEFAULT_SETTINGS)
        if not self.set_wow_path(self._settings.wow_path):
            # try to automatically determine the wow path
            pass


    def _get_addon_path(self, addon=None):
        if not addon:
            return os.path.abspath(os.path.join(self._settings.wow_path, "Interface", "Addons"))
        else:
            return os.path.abspath(os.path.join(self._settings.wow_path, "Interface", "Addons", addon))


    def _addons_folder_changed_delayed(self):
        self._addons_folder_change_scheduled = False
        self.addons_folder_changed.emit()


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
            return False
        if self._settings.wow_path != "":
                self._watcher.removePath(self._get_addon_path())
        self._settings.wow_path = os.path.abspath(path)
        self._watcher.addPath(self._get_addon_path())
        logging.getLogger().info("WoW path is set to '{}'".format(self._settings.wow_path))
        self._valid_wow_path = True
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
