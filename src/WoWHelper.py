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
import logging
import os


class WoWHelper:
    INVALID_VERSION = 0
    RELEASE_VERSION = 1
    BETA_VERSION = 2
    DEV_VERSION = 3


    def __init__(self):
        self._settings = load_settings(Config.DEFAULT_SETTINGS)
        self.set_wow_path(self._settings.wow_path)
        logging.getLogger().info("WoW path is set to '{}'".format(self._settings.wow_path))


    def set_wow_path(self, path):
        # We'll validate the WoW folder by checking for Interface/Addons and WTF folders
        if not os.path.isdir(os.path.join(path, "Interface", "Addons")) and os.path.isdir(os.path.join(path, "WTF")):
            self._settings.wow_path = ""
            return False
        self._settings.wow_path = path
        return True


    def get_installed_version(self, addon):
        if self._settings.wow_path == "":
            return self.INVALID_VERSION, 0, ""
        # look at the addon's TOC file to get the current version
        toc_path = os.path.join(self._settings.wow_path, "Interface", "Addons", addon, "{}.toc".format(addon))
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
            return self.BETA_VERSION, parts[0] * 1000 + parts[1], version_str
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
