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
from login_window_ui import Ui_LoginWindow

# PyQt5
from PyQt5.QtCore import pyqtSignal, QFile, QIODevice, pyqtSlot, Qt
from PyQt5.QtWidgets import QMainWindow


class LoginWindow(QMainWindow):
    login_button_clicked = pyqtSignal(str, str)


    def __init__(self):
        # Init the base class
        QMainWindow.__init__(self)
        
        # Init the processed .ui file
        self._ui = Ui_LoginWindow()
        self._ui.setupUi(self)
        self.setWindowTitle("TSM Login - r{}".format(Config.CURRENT_VERSION))

        # connect signals / slots
        self._ui.login_button.clicked.connect(self._login_button_clicked)

        # Apply the stylesheet
        file = QFile(":/resources/login_window.css")
        file.open(QIODevice.ReadOnly)
        data = str(file.readAll(), encoding="ascii")
        self.setStyleSheet(data)


    def _login_button_clicked(self, checked):
        self.login_button_clicked.emit(self._ui.email_editbox.text(), self._ui.password_editbox.text())


    def set_enabled(self, enabled):
        self._ui.email_editbox.setEnabled(enabled)
        self._ui.password_editbox.setEnabled(enabled)
        self._ui.login_button.setEnabled(enabled)


    def set_form_values(self, email, password):
        self._ui.email_editbox.setText(email)
        self._ui.password_editbox.setText(password)


    def set_button_text(self, button_text):
        self._ui.login_button.setText(button_text)


    def set_error_text(self, error_text):
        self._ui.error_label.setText(error_text)
