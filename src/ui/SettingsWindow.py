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
from settings_window_ui import Ui_SettingsWindow

# PyQt5
from PyQt5.QtCore import pyqtSignal, QCoreApplication, QFile, QIODevice, QStandardPaths, Qt, QTimer, QUrl
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtWidgets import QCheckBox, QFileDialog, QMainWindow, QMessageBox

# General python modules
from datetime import timedelta
import logging
import os


class SettingsWindow(QMainWindow):
    settings_changed = pyqtSignal(str)
    upload_log_file = pyqtSignal()
    reset_settings = pyqtSignal()


    def __init__(self, parent):
        # Init the base class
        QMainWindow.__init__(self, parent);
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)

        self._ignore_changes = False
        self._settings = load_settings(Config.DEFAULT_SETTINGS)
        
        # Init the processed .ui file
        self._ui = Ui_SettingsWindow()
        self._ui.setupUi(self)
        self.setWindowTitle("Settings - r{}".format(Config.CURRENT_VERSION))

        # connect signals / slots
        self._ui.realm_setup_button.setProperty("url", "http://tradeskillmaster.com/realms")
        self._ui.realm_setup_button.clicked.connect(self._link_button_clicked)
        self._ui.open_backups_button.clicked.connect(self._open_backups)
        self._ui.upload_log_button.clicked.connect(self.upload_log_button_clicked)
        self._ui.done_button.clicked.connect(self.hide)
        self._ui.wow_dir_browse_button.clicked.connect(self.wow_dir_button_clicked)
        self._ui.reset_button.clicked.connect(self.reset_button_clicked)
        self._settings_widgets = {
            'run_at_startup': self._ui.run_at_startup_checkbox,
            'start_minimized': self._ui.start_minimized_checkbox,
            'minimize_to_tray': self._ui.minimize_to_tray_checkbox,
            'confirm_exit': self._ui.confirm_exit_checkbox,
            'tsm3_beta': self._ui.tsm3_beta_checkbox,
            'realm_data_notification': self._ui.realm_data_notification_checkbox,
            'addon_notification': self._ui.addon_notification_checkbox,
            'backup_notification': self._ui.backup_notification_checkbox,
        }
        for setting_key, widget in self._settings_widgets.items():
            if isinstance(widget, QCheckBox):
                widget.stateChanged.connect(self.checkbox_changed)
                widget.setProperty("setting_key", setting_key)

        # populate dropdowns
        def get_seconds(**kwargs):
            return int(timedelta(**kwargs).total_seconds())

        # populate backup period dropdown
        self._backup_period_text = ["30 minutes", "1 hour", "3 hours", "12 hours", "1 day", "3 days"]
        self._backup_period_value = [get_seconds(minutes=30), get_seconds(hours=1), get_seconds(hours=3), get_seconds(hours=12), get_seconds(days=1), get_seconds(days=3)]
        assert(len(self._backup_period_text) == len(self._backup_period_value))
        for item in self._backup_period_text:
            self._ui.backup_period_dropdown.addItem(item)
        if self._settings.backup_period not in self._backup_period_value:
            logging.getLogger().warning("Resetting backup expiration to default")
            self._settings.backup_period = Config.DEFAULT_SETTINGS['backup_period']
        self._ui.backup_period_dropdown.setCurrentIndex(self._backup_period_value.index(self._settings.backup_period))
        self._ui.backup_period_dropdown.activated['int'].connect(self.backup_period_dropdown_changed)

        # populate backup expiration dropdown
        self._backup_expire_text = ["3 days", "1 week", "1 month", "1 year"]
        self._backup_expire_value = [get_seconds(days=3), get_seconds(days=7), get_seconds(days=30), get_seconds(days=365)]
        assert(len(self._backup_expire_text) == len(self._backup_expire_value))
        for item in self._backup_expire_text:
            self._ui.backup_expiration_dropdown.addItem(item)
        if self._settings.backup_expire not in self._backup_expire_value:
            logging.getLogger().warning("Resetting backup expiration to default")
            self._settings.backup_expire = Config.DEFAULT_SETTINGS['backup_expire']
        self._ui.backup_expiration_dropdown.setCurrentIndex(self._backup_expire_value.index(self._settings.backup_expire))
        self._ui.backup_expiration_dropdown.activated['int'].connect(self.backup_expire_dropdown_changed)

        # Apply the stylesheet
        file = QFile(":/resources/settings_window.css")
        file.open(QIODevice.ReadOnly)
        data = str(file.readAll(), encoding="ascii")
        self.setStyleSheet(data)

        # stylesheet tweaks for things which don't work when put into the .css for some unknown reason
        self._ui.general_tab.setStyleSheet("QCheckBox:disabled { color : #666; } QCheckBox { color : white; }");
        self._ui.notifications_tab.setStyleSheet("QCheckBox:disabled { color : #666; } QCheckBox { color : white; }");
        self._ui.advanced_tab.setStyleSheet("QCheckBox:disabled { color : #666; } QCheckBox { color : white; }");


    def on_settings_changed(self):
        self._ignore_changes = True
        for setting_key, widget in self._settings_widgets.items():
            widget.setChecked(getattr(self._settings, setting_key))
        self._ui.wow_dir_editbox.setText(self._settings.wow_path)
        self._ui.tsm3_beta_checkbox.setEnabled(self._settings.has_beta_access)
        self._ignore_changes = False


    def checkbox_changed(self, checked):
        if self._ignore_changes:
            return
        setting_key = self.sender().property("setting_key")
        setattr(self._settings, setting_key, checked == Qt.Checked)


    def backup_period_dropdown_changed(self, index):
        self._settings.backup_period = self._backup_period_value[index]


    def backup_expire_dropdown_changed(self, index):
        self._settings.backup_expire = self._backup_expire_value[index]


    def wow_dir_button_clicked(self):
        prev_dir = self._settings.wow_path
        dir = QFileDialog.getExistingDirectory(self, "Select WoW Directory", os.pardir if prev_dir == "" else prev_dir, QFileDialog.ShowDirsOnly)
        if dir == "":
            # canceled
            return
        self.settings_changed.emit(dir)
        if self._settings.wow_path == "":
            # this was not a valid WoW directory - restore the previous directory and show an error
            self.settings_changed.emit(prev_dir)
            msg_box = QMessageBox()
            msg_box.setWindowIcon(QIcon(":/resources/logo.png"))
            msg_box.setWindowModality(Qt.ApplicationModal)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText("Invalid WoW Directory")
            msg_box.setTextFormat(Qt.RichText)
            msg_box.setInformativeText("The WoW directory you have selected is not valid. Please select the base 'World of Warcraft' directory.")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
        self._ui.wow_dir_editbox.setText(self._settings.wow_path)


    def upload_log_button_clicked(self):
        self._ui.upload_log_button.setEnabled(False)
        self._ui.upload_log_button.setText("Uploading...")
        # slight delay so the button gets disabled
        QTimer.singleShot(1, self.upload_log_file.emit)


    def reset_button_clicked(self):
        self.hide()
        self.reset_settings.emit()


    def _link_button_clicked(self):
        QDesktopServices.openUrl(QUrl(self.sender().property("url")))


    def _open_backups(self):
        QDesktopServices.openUrl(QUrl("file:///{}".format(os.path.join(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation), "Backups"))))


    def log_uploaded(self, success):
        self._ui.upload_log_button.setEnabled(True)
        self._ui.upload_log_button.setText("Upload App Log")
        # show a popup saying whether or not it was successful
        msg_box = QMessageBox()
        msg_box.setWindowIcon(QIcon(":/resources/logo.png"))
        msg_box.setWindowModality(Qt.ApplicationModal)
        msg_box.setIcon(QMessageBox.Information)
        if success:
            msg_box.setText("Uploaded App Log")
            msg_box.setInformativeText("Your log file has been successfully uploaded!")
        else:
            msg_box.setText("App Log Upload Failed")
            msg_box.setInformativeText("Failed to upload your app log. After you close this dialog, the log file will be opened in a text editor so you can manually copy-paste it into a pastebin (http://pastebin.com).")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
        if not success:
            # open up the file so they can manually upload it to a pastebin
            QDesktopServices.openUrl(QUrl("file:///{}".format(os.path.join(os.getcwd(), Config.LOG_FILE_NAME))))
