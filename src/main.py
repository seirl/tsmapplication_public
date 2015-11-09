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
from MainThread import MainThread
import Config
from Settings import load_settings
from ui.LoginWindow import LoginWindow
from ui.MainWindow import MainWindow

# PyQt5
from PyQt5.QtCore import QObject, QByteArray, QSettings
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox

# General python modules
import logging
from logging.handlers import RotatingFileHandler
import os
import traceback
import sys


class TSMApp(QObject):
    def __init__(self):
        QObject.__init__(self)
        # Create the QApplication
        self._app = QApplication(sys.argv)
        self._app.setOrganizationName(Config.ORG_NAME)
        self._app.setApplicationName(Config.APP_NAME)

        # initialize the logger
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s", datefmt="%m/%d/%Y %H:%M:%S")
        self._logger = logging.getLogger()
        self._logger.setLevel(logging.DEBUG)
        handler = RotatingFileHandler(Config.LOG_FILE_NAME, mode='w', maxBytes=200000, backupCount=1)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s", "%m/%d/%Y %H:%M:%S"))
        handler.doRollover() # clear the log everytime we start
        self._logger.addHandler(handler)


    # def show_terms_of_use(self):
        # accepted = self._main_window.show_message_box(QMessageBox.Warning, "TradeSkillMaster Application Terms of Use", "By clicking 'OK' you are acknowledging acceptance of the <a href='http://www.tradeskillmaster.com/site/terms'>TSM Terms of Use</a>.<br>If you do not accept the terms, click cancel to close the application.", True)
        # if not accepted:
            # # They didn't accept, so exit
            # sys.exit(0)
        # self._settings.accepted_terms = True


    def run(self):
        self._logger.info("Starting TSM Application r{}".format(Config.CURRENT_VERSION))

        # Create the windows
        self._login_window = LoginWindow()
        self._main_window = MainWindow()

        # Setup the main thread which handles all the business logic
        self._main_thread = MainThread()
        # connect login window signals / slots
        self._login_window.login_button_clicked.connect(self._main_thread.login_button_clicked)
        self._main_thread.set_login_window_visible.connect(self._login_window.setVisible)
        self._main_thread.set_login_window_enabled.connect(self._login_window.set_enabled)
        self._main_thread.set_login_window_form_values.connect(self._login_window.set_form_values)
        self._main_thread.set_login_window_button_text.connect(self._login_window.set_button_text)
        self._main_thread.set_login_window_error_text.connect(self._login_window.set_error_text)
        # set main window signals / slots
        self._main_thread.set_main_window_visible.connect(self._main_window.setVisible)
        self._main_thread.set_main_window_header_text.connect(self._main_window._ui.header_text.setText)
        self._main_thread.set_main_window_sync_status_data.connect(self._main_window.set_sync_status_data)
        self._main_thread.set_main_window_addon_status_data.connect(self._main_window.set_addon_status_data)
        # set general signals / slots
        self._main_thread.finished.connect(self._app.exit)
        # start the thread
        self._main_thread.start()

        # Start the app
        self._app.exec_()


if __name__ == "__main__":
    # Catch and log any exceptions that occur while running the app
    try:
        tsm_app = TSMApp()
        tsm_app.run()
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        logging.getLogger().error("".join(lines))
