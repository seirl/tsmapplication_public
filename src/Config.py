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


import os
import sys


# Constant context parameters
IS_WINDOWS = sys.platform.startswith("win32")
IS_MAC = sys.platform.startswith("darwin")
assert(IS_WINDOWS != IS_MAC) # only one should be set


# General app constants
ORG_NAME = "TradeSkillMaster"
APP_NAME = "TSMApplication"
CURRENT_VERSION = 300
LOG_FILE_PATH = None
STATUS_CHECK_INTERVAL_S = 10 * 60
APP_API_BASE_URL = "http://app-server.tradeskillmaster.com/v1"
BACKUP_TIME_FORMAT = "%Y%m%d%H%M%S"
BACKUP_NAME_SEPARATOR = "_"
MAX_BLACK_MARKET_AGE = 24 * 60 * 60
UPDATER_PATH = os.path.join("updater", "TSMUpdater.exe") if IS_WINDOWS else os.path.join("updater", "TSMUpdater")

# close reasons
CLOSE_REASON_NORMAL = 0
CLOSE_REASON_CRASH = 1
CLOSE_REASON_UPDATE = 2

# Default settings
DEFAULT_SETTINGS = {
    'version': 0,
    'email': "",
    'password': "",
    'accepted_terms': False,
    'wow_path': "",
    'tsm3_beta': False,
    'has_beta_access': False,
    'run_at_startup': True,
    'start_minimized': False,
    'minimize_to_tray': True,
    'confirm_exit': True,
    'backup_period': 30 * 60,
    'backup_expire': 30 * 24 * 60 * 60,
    'realm_data_notification': True,
    'addon_notification': True,
    'backup_notification': True,
    'close_reason': CLOSE_REASON_NORMAL,
}
DEFAULT_OLD_LOGIN_SETTINGS = {
    'userId': 0,
    'email': "",
    'password': b"",
    'touAccepted': "false",
}
