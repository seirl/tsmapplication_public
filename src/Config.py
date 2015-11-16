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


# General app constants
ORG_NAME = "TradeSkillMaster"
APP_NAME = "TSMApplication"
CURRENT_VERSION = 300
LOG_FILE_NAME = "TSMApplication.log"
STATUS_CHECK_INTERVAL_S = 10 * 60
APP_API_BASE_URL = "http://old-app-server.tradeskillmaster.com/app"

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
}
DEFAULT_OLD_LOGIN_SETTINGS = {
    'userId': 0,
    'email': "",
    'password': b"",
    'touAccepted': "false",
}
