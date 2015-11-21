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
from main_window_ui import Ui_MainWindow
from ui.TableModel import TableModel

# PyQt5
from PyQt5.QtCore import pyqtSignal, QFile, QIODevice, Qt, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox


class MainWindow(QMainWindow):
    settings_button_clicked = pyqtSignal()
    addon_status_table_clicked = pyqtSignal(str)
    accounting_account_selected = pyqtSignal(str)


    def __init__(self):
        # Init the base class
        QMainWindow.__init__(self)
        
        # Init the processed .ui file
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)
        self.setWindowTitle("TradeSkillMaster Application r{}".format(Config.CURRENT_VERSION))

        # connect signals / slots
        self._ui.addon_status_table.doubleClicked.connect(self._addon_status_table_clicked)
        self._ui.settings_button.clicked.connect(self.settings_button_clicked.emit)
        self._ui.accounting_accounts_dropdown.activated['QString'].connect(self.accounting_accounts_dropdown_changed)

        # Apply the stylesheet
        file = QFile(":/resources/main_window.css")
        file.open(QIODevice.ReadOnly)
        data = str(file.readAll(), encoding="ascii")
        self.setStyleSheet(data)

        # set properties which are necessary for tweaking the style
        self._ui.premium_button.setProperty("id", "premiumButton")
        self._ui.header.setProperty("id", "headerText")

        self._sync_status_table_model = TableModel(self, ['Realm', 'AuctionDB', 'WoWuction', 'Great Deals'])
        self._ui.sync_status_table.setModel(self._sync_status_table_model)

        self._addon_status_table_model = TableModel(self, ['Name', 'Version', 'Status'])
        self._ui.addon_status_table.setModel(self._addon_status_table_model)


    def _addon_status_table_clicked(self, index):
        key = self._addon_status_table_model.get_click_key(index)
        if key:
            self.addon_status_table_clicked.emit(key)


    def set_sync_status_data(self, data):
        self._sync_status_table_model.set_info(data)
        self._ui.sync_status_table.resizeColumnsToContents()
        self._ui.sync_status_table.sortByColumn(0, Qt.AscendingOrder)


    def set_addon_status_data(self, data):
        self._addon_status_table_model.set_info(data)
        self._ui.addon_status_table.resizeColumnsToContents()
        self._ui.addon_status_table.sortByColumn(0, Qt.AscendingOrder)


    def set_accounting_accounts(self, accounts):
        self._ui.accounting_accounts_dropdown.clear()
        self._ui.accounting_accounts_dropdown.addItem("")
        for account in accounts:
            self._ui.accounting_accounts_dropdown.addItem(account)


    def accounting_accounts_dropdown_changed(self, account):
        # slight delay so the button gets disabled
        def emit_signal():
            self.accounting_account_selected.emit(account)
        QTimer.singleShot(1, emit_signal)
