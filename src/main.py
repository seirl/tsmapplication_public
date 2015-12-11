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
from ui.SettingsWindow import SettingsWindow

# PyQt5
from PyQt5.QtCore import pyqtSignal, QObject, QStandardPaths, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox

# General python modules
import logging
from logging.handlers import RotatingFileHandler
import os
import traceback
import sys


class TSMApp(QObject):
    terms_accepted = pyqtSignal()


    def __init__(self):
        QObject.__init__(self)
        self._settings = None
        # Create the QApplication
        self._app = QApplication(sys.argv)
        self._app.setOrganizationName(Config.ORG_NAME)
        self._app.setApplicationName(Config.APP_NAME)

        # initialize the logger
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s", datefmt="%m/%d/%Y %H:%M:%S")
        self._logger = logging.getLogger()
        # remove default (stdout) handler
        self._logger.handlers = []
        self._logger.setLevel(logging.DEBUG)
        app_data_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        os.makedirs(app_data_dir, exist_ok=True)
        Config.LOG_FILE_PATH = os.path.join(app_data_dir, "TSMApplication.log")
        handler = RotatingFileHandler(Config.LOG_FILE_PATH, mode='w', maxBytes=200000, backupCount=1)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s", "%m/%d/%Y %H:%M:%S"))
        handler.doRollover() # clear the log everytime we start
        self._logger.addHandler(handler)


    def run(self):
        self._logger.info("Starting TSM Application r{}".format(Config.CURRENT_VERSION))

        # Create the windows
        self._login_window = LoginWindow()
        self._main_window = MainWindow()
        self._settings_window = SettingsWindow(self._main_window)
        self._settings = load_settings(Config.DEFAULT_SETTINGS)

        # Setup the main thread which handles all the business logic
        self._main_thread = MainThread()
        # connect login window signals / slots
        self._login_window.login_button_clicked.connect(self._main_thread.login_button_clicked)
        self._main_thread.set_login_window_visible.connect(self._login_window.setVisible)
        self._main_thread.set_login_window_enabled.connect(self._login_window.set_enabled)
        self._main_thread.set_login_window_form_values.connect(self._login_window.set_form_values)
        self._main_thread.set_login_window_button_text.connect(self._login_window.set_button_text)
        self._main_thread.set_login_window_error_text.connect(self._login_window.set_error_text)
        # connect main window signals / slots
        self._main_window.settings_button_clicked.connect(self._settings_window.show)
        self._main_window.status_table_clicked.connect(self._main_thread.status_table_clicked, Qt.QueuedConnection)
        self._main_window.export_accounting.connect(self._main_thread.accounting_export)
        self._main_thread.set_main_window_visible.connect(self._main_window.setVisible)
        self._main_thread.set_main_window_header_text.connect(self._main_window._ui.header_text.setText)
        self._main_thread.set_main_window_sync_status_data.connect(self._main_window.set_sync_status_data)
        self._main_thread.set_main_window_addon_status_data.connect(self._main_window.set_addon_status_data)
        self._main_thread.set_main_window_backup_status_data.connect(self._main_window.set_backup_status_data)
        self._main_thread.set_main_window_accounting_accounts.connect(self._main_window.set_accounting_accounts)
        self._main_thread.show_desktop_notification.connect(self._main_window.show_notification)
        self._main_thread.set_main_window_title.connect(self._main_window.setWindowTitle)
        self._main_thread.set_main_window_premium_button_visible.connect(self._main_window._ui.premium_button.setVisible)
        # connect settings window signals / slots
        self._settings_window.settings_changed.connect(self._main_thread.on_settings_changed)
        self._settings_window.upload_log_file.connect(self._main_thread.upload_log_file)
        self._settings_window.reset_settings.connect(self._main_thread.reset_settings)
        self._settings_window.run_at_startup_changed.connect(self._main_thread.update_run_at_startup)
        self._main_thread.settings_changed.connect(self._settings_window.on_settings_changed)
        self._main_thread.log_uploaded.connect(self._settings_window.log_uploaded)
        # connect general signals / slots
        self._main_thread.finished.connect(self._app.exit)
        self._main_thread.show_terms.connect(self.show_terms)
        self.terms_accepted.connect(self._main_thread.terms_accepted)
        self._main_thread.run_updater.connect(self.run_updater)
        # start the thread
        self._main_thread.start()

        # Start the app
        self._app.exec_()


    def run_updater(self):
        self._settings.close_reason = Config.CLOSE_REASON_UPDATE
        self._logger.warn("Running updater!")
        sys.argv[0] = os.path.abspath(os.path.join(os.path.dirname(sys.executable), os.pardir, Config.UPDATER_PATH))
        os.execl(sys.argv[0], *sys.argv)


    def show_terms(self):
        msg_box = QMessageBox()
        msg_box.setWindowIcon(QIcon(":/resources/logo.png"))
        msg_box.setWindowModality(Qt.ApplicationModal)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText("TradeSkillMaster Application Terms of Use")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setInformativeText("By clicking 'OK' you are agreeing to the <a href='http://www.tradeskillmaster.com/site/terms'>TSM Terms of Use</a>.<br>If you do not accept the terms, click cancel to close the application.")
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg_box.setDefaultButton(QMessageBox.Cancel)
        if msg_box.exec_() != QMessageBox.Ok:
            # They didn't accept, so exit
            sys.exit(0)
        self.terms_accepted.emit()


if __name__ == "__main__":
    # Catch and log any exceptions that occur while running the app
    tsm_app = None
    try:
        tsm_app = TSMApp()
        tsm_app.run()
        # the user closed the app normally
        tsm_app._settings.close_reason = Config.CLOSE_REASON_NORMAL
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        logging.getLogger().error("".join(lines))
        if tsm_app:
            tsm_app._settings.close_reason = Config.CLOSE_REASON_CRASH
        raise
