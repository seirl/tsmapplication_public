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

# The purpose of this script is to facilitate the TSM Application automatically updating itself. When an update is
# available, the main app (running out of "app/") will download it to an "app_new/" folder and then run this script.
# This script will then replace the "app/" folder with the "app_new/" folder and restart the app. Ideally, this script
# should be super robust, and never crash, as if it fails the user will likely be left with a corrupted install.

import os
from shutil import rmtree, copytree
import sys
import time

APP_NAME = "TSMApplication.exe" if sys.platform.startswith("win32") else "TSMApplication"


class TSMUpdater:
    def __init__(self):
        # the CWD is still within the app folder - we need to change it so we are able to delete the app folder
        self._cwd = os.path.abspath(os.path.join(os.path.dirname(sys.executable), os.pardir))
        os.chdir(self._cwd)

        # create a log file in case something goes wrong
        try:
            self._log_file = open(os.path.join(self._cwd, "updater", "update.log"), 'w')
        except:
            # we couldn't create the log file - we're living dangerously now, but keep going
            self._log_file = None


    def _close_log(self):
        if self._log_file:
            self._log_file.flush()
            self._log_file.close()
            self._log_file = None


    def _log_msg(self, msg):
        if not self._log_file:
            return
        try:
            self._log_file.write("{}: {}\n".format(time.strftime("%m/%d/%Y %H:%M:%S"), str(msg)))
        except:
            # we failed to write to the log file - we're probably screwed, but let the script keep going
            pass


    def run(self):
        try:
            if not os.path.isdir(self._cwd, "app_new"):
                self._log_msg("The app_new folder doesn't exit!")
                sys.exit(1)
            self._log_msg("Swapping folders...")
            # brief sleep to make sure the app closed completely
            time.sleep(1)
            # remove the old app folder
            rmtree(os.path.join(self._cwd, "app"))
            # move the new app folder
            copytree(os.path.join(self._cwd, "app_new"), os.path.join(self._cwd, "app"))
            rmtree(os.path.join(self._cwd, "app_new"))
            # brief sleep to let the folder updates settle
            time.sleep(1)
            self._log_msg("Success!")
            self._log_msg("Launching app ({})!".format(os.path.join(self._cwd, "app", APP_NAME)))
            self._close_log()
            # run the new app
            sys.argv = [os.path.join(self._cwd, "app", APP_NAME)]
            os.execl(sys.argv[0], *sys.argv)
        except:
            # well this is bad...hopefully we can at least log what happened
            import traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            self._log_msg("".join(lines))


updater = TSMUpdater()
updater.run()
assert(False) # should never get here
