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


from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import Qt, QFile, QIODevice

from ui.TableModel import TableModel
from main_window_ui import Ui_MainWindow

class MainWindow(QMainWindow):
    def __init__(self):
        # Init the base class
        QMainWindow.__init__(self)
        
        # Init the processed .ui file
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)

        # Apply the stylesheet
        file = QFile(":/resources/style.css")
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

    def set_sync_status_data(self, data):
        self._sync_status_table_model.setData(data)
        self._ui.sync_status_table.resizeColumnsToContents()
        self._ui.sync_status_table.sortByColumn(0, Qt.AscendingOrder)

    def set_addon_status_data(self, data):
        self._addon_status_table_model.setData(data)
        self._ui.addon_status_table.resizeColumnsToContents()
        self._ui.addon_status_table.sortByColumn(0, Qt.AscendingOrder)