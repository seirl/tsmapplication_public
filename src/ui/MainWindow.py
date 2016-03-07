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
from Settings import load_settings
from ui.TableModel import TableModel

# PyQt5
from PyQt5.QtCore import pyqtSignal, QEvent, QFile, QIODevice, Qt, QTimer, QUrl
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtWidgets import QAction, QApplication, QMainWindow, QMenu, QMessageBox, QSystemTrayIcon

# General python modules
import logging


class MainWindow(QMainWindow):
    settings_button_clicked = pyqtSignal()
    status_table_clicked = pyqtSignal(str)
    export_accounting = pyqtSignal(str, str, str)


    def __init__(self):
        # Init the base class
        QMainWindow.__init__(self)

        self._settings = load_settings(Config.DEFAULT_SETTINGS)

        # Init the processed .ui file
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)
        self.setWindowTitle("TradeSkillMaster Application r{}".format(Config.CURRENT_VERSION))

        # connect signals / slots
        self._ui.addon_status_table.doubleClicked.connect(self._addon_status_table_clicked)
        self._ui.backup_status_table.doubleClicked.connect(self._backup_status_table_clicked)
        self._ui.settings_button.clicked.connect(self.settings_button_clicked.emit)
        self._ui.accounts_dropdown.activated['QString'].connect(self.accounts_dropdown_changed)
        self._ui.realm_dropdown.activated['QString'].connect(self.realm_dropdown_changed)
        self._ui.export_button.clicked.connect(self.export_button_clicked)
        self._ui.help_button.setProperty("url", "http://tradeskillmaster.com/site/getting-help")
        self._ui.help_button.clicked.connect(self._link_button_clicked)
        self._ui.premium_button.setProperty("url", "http://tradeskillmaster.com/premium")
        self._ui.premium_button.clicked.connect(self._link_button_clicked)
        self._ui.logo_button.setProperty("url", "http://tradeskillmaster.com")
        self._ui.logo_button.clicked.connect(self._link_button_clicked)
        self._ui.twitter_button.setProperty("url", "http://twitter.com/TSMAddon")
        self._ui.twitter_button.clicked.connect(self._link_button_clicked)

        # Apply the stylesheet
        file = QFile(":/resources/main_window.css")
        file.open(QIODevice.ReadOnly)
        data = str(file.readAll(), encoding="ascii")
        self.setStyleSheet(data)

        # set properties which are necessary for tweaking the style
        self._ui.help_button.setProperty("id", "premiumButton")
        self._ui.premium_button.setProperty("id", "premiumButton")
        self._ui.header_text.setProperty("id", "headerText")

        # stylesheet tweaks for things which don't work when put into the .css for some unknown reason
        self._ui.accounting_tab.setStyleSheet("QCheckBox:disabled { color : #666; } QCheckBox { color : white; }");

        self._sync_status_table_model = TableModel(self, ['Region/Realm', 'AuctionDB', 'Great Deals', 'Last Updated'])
        self._ui.sync_status_table.setModel(self._sync_status_table_model)

        self._addon_status_table_model = TableModel(self, ['Name', 'Version', 'Status'])
        self._ui.addon_status_table.setModel(self._addon_status_table_model)

        self._backup_status_table_model = TableModel(self, ['System ID', 'Account', 'Timestamp', 'Notes'])
        self._ui.backup_status_table.setModel(self._backup_status_table_model)

        self._accounting_info = {}
        self._accounting_current_account = ""
        self._accounting_current_realm = ""

        if Config.IS_WINDOWS:
            # create the system tray icon / menu
            self._tray_icon = QSystemTrayIcon(QIcon(":/resources/logo.png"), self)
            self._tray_icon.setToolTip("TradeSkillMaster Application r{}".format(Config.CURRENT_VERSION))
            self._tray_icon.activated.connect(self._icon_activated)
            tray_icon_menu = QMenu(self)
            restore_action = QAction("Restore", tray_icon_menu)
            restore_action.triggered.connect(self._restore_from_tray)
            tray_icon_menu.addAction(restore_action)
            tray_icon_menu.addSeparator()
            quit_action = QAction("Quit", tray_icon_menu)
            quit_action.triggered.connect(self.close)
            tray_icon_menu.addAction(quit_action)
            self._tray_icon.setContextMenu(tray_icon_menu)
            self._tray_icon.hide()


    def __del__(self):
        if Config.IS_WINDOWS:
            self._tray_icon.hide()


    def changeEvent(self, event):
        if not Config.IS_WINDOWS:
            return
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized() and self._settings.minimize_to_tray:
                logging.getLogger().info("Minimizing to the system tray")
                self._tray_icon.show()
                self.hide()
                event.ignore()


    def closeEvent(self, event):
        if self._settings.confirm_exit:
            msg_box = QMessageBox()
            msg_box.setWindowIcon(QIcon(":/resources/logo.png"))
            msg_box.setWindowModality(Qt.ApplicationModal)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setText("Are you sure you want to exit?")
            msg_box.setStandardButtons(QMessageBox.Cancel | QMessageBox.Yes)
            if msg_box.exec_() != QMessageBox.Yes:
                event.ignore()
                return
        event.accept()


    def set_visible(self, visible):
        self.setVisible(visible)
        if self._settings.start_minimized and Config.IS_WINDOWS:
            self.showMinimized()
            self.setWindowState(Qt.WindowMinimized)
            if self._settings.minimize_to_tray:
                logging.getLogger().info("Minimizing to the system tray")
                self._tray_icon.show()
                self.hide()
            else:
                logging.getLogger().info("Minimizing")


    def _restore_from_tray(self):
        if not Config.IS_WINDOWS:
            return
        logging.getLogger().info("Restoring from the system tray")
        self.show()
        self.setWindowState(Qt.WindowActive)
        self._tray_icon.hide()


    def _icon_activated(self, reason):
        if not Config.IS_WINDOWS:
            return
        if reason == QSystemTrayIcon.Trigger or reason == QSystemTrayIcon.DoubleClick:
            self._restore_from_tray()


    def _link_button_clicked(self):
        QDesktopServices.openUrl(QUrl(self.sender().property("url")))


    def _addon_status_table_clicked(self, index):
        key = self._addon_status_table_model.get_click_key(index)
        if key:
            self.status_table_clicked.emit(key)


    def _backup_status_table_clicked(self, index):
        key = self._backup_status_table_model.get_click_key(index)
        if key:
            self.status_table_clicked.emit(key)


    def set_sync_status_data(self, data):
        self._sync_status_table_model.set_info(data)
        self._ui.sync_status_table.resizeColumnsToContents()
        self._ui.sync_status_table.sortByColumn(0, Qt.AscendingOrder)


    def set_addon_status_data(self, data):
        self._addon_status_table_model.set_info(data)
        self._ui.addon_status_table.resizeColumnsToContents()
        self._ui.addon_status_table.sortByColumn(0, Qt.AscendingOrder)


    def set_backup_status_data(self, data):
        system_text = "The system ID is unique to the computer you are running the desktop app from. " + \
                      "<a href=\"http://tradeskillmaster.com/premium\" style=\"color: #EC7800\">Premium users</a> " + \
                      "can sync backups to the cloud and across multiple computers. Otherwise, only backups from the " + \
                      "local system (<font style=\"color: cyan\">{}</font>) will be listed below." \
                      .format(self._settings.system_id)
        self._ui.backup_system_text.setText(system_text)
        self._backup_status_table_model.set_info(data)
        self._ui.backup_status_table.resizeColumnsToContents()
        self._ui.backup_status_table.sortByColumn(2, Qt.DescendingOrder)


    def show_notification(self, message, critical):
        if not Config.IS_WINDOWS:
            return
        icon = QSystemTrayIcon.Critical if critical else QSystemTrayIcon.NoIcon
        if self._tray_icon.isVisible():
            self._tray_icon.showMessage("TradeSkillMaster Desktop Application", message, icon)
        else:
            # The tray icon needs to be visible to show the message, but we can immediately hide it afterwards
            # This is the behavior on Windows 10 at least...need to confirm on other operating systems
            self._tray_icon.show()
            self._tray_icon.showMessage("TradeSkillMaster Desktop Application", message, icon)
            self._tray_icon.hide()


    def _update_dropdown(self, dropdown, items, selected_item):
        items = [""] + items
        selected_index = 0
        dropdown.clear()
        for index, item in enumerate(items):
            if item == selected_item:
                selected_index = index
            dropdown.addItem(item)
        dropdown.setCurrentIndex(selected_index)


    def _update_accounting_tab(self):
        # update the accounts dropdown
        accounts = [x for x in self._accounting_info if self._accounting_info[x]]
        self._update_dropdown(self._ui.accounts_dropdown, accounts, self._accounting_current_account)

        # update the realm dropdown
        self._ui.realm_dropdown.setEnabled(self._accounting_current_account != "")
        if self._accounting_current_account != "":
            self._update_dropdown(self._ui.realm_dropdown,
                                  self._accounting_info[self._accounting_current_account],
                                  self._accounting_current_realm)

        # update the export button
        self._ui.export_button.setEnabled(self._accounting_current_realm != "")


    def set_accounting_accounts(self, info):
        self._accounting_info = info
        self._update_accounting_tab()


    def accounts_dropdown_changed(self, account):
        self._accounting_current_account = account
        self._accounting_current_realm = ""
        self._update_accounting_tab()


    def realm_dropdown_changed(self, realm):
        assert(self._accounting_current_account)
        self._accounting_current_realm = realm
        self._update_accounting_tab()


    def export_button_clicked(self):
        self._ui.export_button.setEnabled(False)
        self._ui.export_button.setText("Exporting...")
        def do_export():
            if self._ui.sales_checkbox.checkState():
                self.export_accounting.emit(self._accounting_current_account, self._accounting_current_realm, "sales")
            if self._ui.purchases_checkbox.checkState():
                self.export_accounting.emit(self._accounting_current_account, self._accounting_current_realm, "purchases")
            if self._ui.income_checkbox.checkState():
                self.export_accounting.emit(self._accounting_current_account, self._accounting_current_realm, "income")
            if self._ui.expenses_checkbox.checkState():
                self.export_accounting.emit(self._accounting_current_account, self._accounting_current_realm, "expenses")
            if self._ui.expired_checkbox.checkState():
                self.export_accounting.emit(self._accounting_current_account, self._accounting_current_realm, "expired")
            if self._ui.canceled_checkbox.checkState():
                self.export_accounting.emit(self._accounting_current_account, self._accounting_current_realm, "canceled")
            self._ui.export_button.setEnabled(True)
            self._ui.export_button.setText("Export to CSV")

            # show a popup saying we've exported everything
            msg_box = QMessageBox()
            msg_box.setWindowIcon(QIcon(":/resources/logo.png"))
            msg_box.setWindowModality(Qt.ApplicationModal)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setText("The TSM_Accounting data has been successfully exported to your desktop.")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
        # slight delay so the button gets disabled
        QTimer.singleShot(1, do_export)
