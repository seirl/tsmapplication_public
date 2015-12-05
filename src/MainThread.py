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
from AppAPI import AppAPI, ApiError, ApiTransientError
import Config
import PrivateConfig
from Settings import load_settings
from WoWHelper import WoWHelper

# PyQt5
from PyQt5.QtCore import pyqtSignal, QDateTime, QMutex, QSettings, QThread, QVariant, QWaitCondition, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMessageBox

# General python modules
from enum import Enum
from hashlib import md5, sha512
from io import BytesIO
import logging
import os
import psutil
import re
import shutil
import sys
from time import strftime, time
import traceback
from zipfile import ZipFile


class MainThread(QThread):
    class WaitEvent(Enum):
        NONE = 0
        LOGIN_BUTTON = 1
        TERMS_ACCEPTED = 2


    class State(Enum):
        INIT = 0
        LOGGED_OUT = 1
        PENDING_NEW_SESSION = 2
        VALID_SESSION = 3
        SLEEPING = 4

        @staticmethod
        def is_valid_transition(old_state, new_state):
            if new_state == MainThread.State.INIT:
                # should never go back to this state
                return False
            elif new_state == MainThread.State.LOGGED_OUT:
                # any current state is valid
                return True
            elif new_state == MainThread.State.PENDING_NEW_SESSION:
                return old_state == MainThread.State.SLEEPING
            elif new_state == MainThread.State.VALID_SESSION:
                return old_state in [MainThread.State.LOGGED_OUT, MainThread.State.PENDING_NEW_SESSION]
            elif new_state == MainThread.State.SLEEPING:
                return old_state == MainThread.State.VALID_SESSION


    set_login_window_visible = pyqtSignal(bool)
    set_login_window_enabled = pyqtSignal(bool)
    set_login_window_form_values = pyqtSignal(str, str)
    set_login_window_button_text = pyqtSignal(str)
    set_login_window_error_text = pyqtSignal(str)
    show_terms = pyqtSignal()
    set_main_window_visible = pyqtSignal(bool)
    set_main_window_header_text = pyqtSignal(str)
    set_main_window_sync_status_data = pyqtSignal(list)
    set_main_window_addon_status_data = pyqtSignal(list)
    set_main_window_backup_status_data = pyqtSignal(list)
    set_main_window_accounting_accounts = pyqtSignal(dict)
    set_main_window_title = pyqtSignal(str)
    settings_changed = pyqtSignal()
    log_uploaded = pyqtSignal(bool)
    show_desktop_notification = pyqtSignal(str, bool)
    run_updater = pyqtSignal()
    set_main_window_premium_button_visible = pyqtSignal(bool)


    def __init__(self):
        # initi parent class and get a refernece to the logger
        QThread.__init__(self)
        self._logger = logging.getLogger()

        # load settings
        self._settings = load_settings(Config.DEFAULT_SETTINGS)
        if self._settings.version == 0:
            # this is the first time we've run r300 or higher
            old_login_settings = load_settings(Config.DEFAULT_OLD_LOGIN_SETTINGS, Config.ORG_NAME, "TSMAppLogin")
            if old_login_settings.userId > 0:
                # import the settings we care about from the old app
                self._settings.email = old_login_settings.email
                self._settings.password = str(old_login_settings.password, encoding="ascii")
                self._settings.accepted_terms = (old_login_settings.touAccepted == "true")
                # need to use QSettings directly for the regular settings since it uses groups / arrays
                old_settings = QSettings(QSettings.IniFormat, QSettings.UserScope, Config.ORG_NAME, "TSMApplication")
                self._settings.wow_path = old_settings.value("core/wowDirPath", Config.DEFAULT_SETTINGS['wow_path'])
                self._settings.tsm3_beta = (WoWHelper().get_installed_version("TradeSkillMaster")[0] == WoWHelper.BETA_VERSION)
                self._logger.info("Imported old settings!")
        self._settings.version = Config.CURRENT_VERSION

        # initialize other helper classes
        self._api = AppAPI()
        self._wow_helper = WoWHelper()
        self._wow_helper.addons_folder_changed.connect(self._update_addon_status)

        # initialize the variables which allow us to wait for signals
        self._wait_event = self.WaitEvent.NONE
        self._wait_context = None
        self._wait_condition = QWaitCondition()
        self._wait_mutex = QMutex()

        # initialize the FSM state and related variables
        self._state = self.State.INIT
        self._sleep_time = 0
        self._addon_versions = []
        self._data_sync_status = {}
        self._last_news = ""
        self._is_logged_out = None


    def _wait_for_event(self, event):
        self._wait_mutex.lock()
        if self._wait_event != self.WaitEvent.NONE:
            raise Exception("Already waiting for event {}".format(self.waiting_key))
        self._wait_event = event
        self._wait_condition.wait(self._wait_mutex)
        self._wait_event = self.WaitEvent.NONE
        self._wait_mutex.unlock()
        context = self._wait_context
        self._wait_context = None
        return context


    def _fire_wait_event(self, event, context=None):
        if self._wait_event != event:
            self._logger.info("Dropping event: {}".format(event))
            return
        self._wait_context = context
        self._wait_condition.wakeAll()


    def terms_accepted(self):
        self._fire_wait_event(self.WaitEvent.TERMS_ACCEPTED)


    def login_button_clicked(self, email, password):
        self._fire_wait_event(self.WaitEvent.LOGIN_BUTTON, (email, password))


    def status_table_clicked(self, click_key):
        parts = click_key.split("~")
        table = parts.pop(0)
        if table == "addon":
            self._download_addon(*parts)
            self._update_addon_status()
        elif table == "backup":
            # check that WoW isn't running
            for p in psutil.process_iter():
                try:
                    if p.cwd() == self._settings.wow_path:
                        # WoW is running
                        msg_box = QMessageBox()
                        msg_box.setWindowIcon(QIcon(":/resources/logo.png"))
                        msg_box.setWindowModality(Qt.ApplicationModal)
                        msg_box.setIcon(QMessageBox.Warning)
                        msg_box.setText("WoW cannot be open while restoring a backup. Please close WoW and try again.")
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.exec_()
                        return
                except psutil.AccessDenied:
                    pass
            success = self._wow_helper.restore_backup(*parts)
            msg_box = QMessageBox()
            msg_box.setWindowIcon(QIcon(":/resources/logo.png"))
            msg_box.setWindowModality(Qt.ApplicationModal)
            msg_box.setIcon(QMessageBox.Information if success else QMessageBox.Warning)
            msg_box.setText("Restored backup successfully!" if success else "Failed to restore backup!")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
        else:
            raise Exception("Invalid table: {}".format(click_key))


    def accounting_export(self, account, realm, key):
        self._wow_helper.export_accounting_csv(account, realm, key)


    def upload_log_file(self):
        data = None
        with open(Config.LOG_FILE_PATH) as log_file:
            data = log_file.read()
        if not data:
            self.log_uploaded.emit(False)
        try:
            self._api.log(data)
            self.log_uploaded.emit(True)
        except (ApiTransientError, ApiError) as e:
            self.log_uploaded.emit(False)


    def on_settings_changed(self, str):
        if self._wow_helper.set_wow_path(str):
            # we just got a valid wow directory so stop sleeping
            self.stop_sleeping()


    def reset_settings(self):
        self._settings.settings.clear()
        self._settings.version = Config.CURRENT_VERSION
        self._wow_helper.set_wow_path("")
        self.stop_sleeping()
        # TODO: fix crash if we're in the middle of the VALID_SESSION state
        self._set_fsm_state(self.State.LOGGED_OUT)


    def stop_sleeping(self):
        self._sleep_time = 0


    def _download_addon(self, addon, version):
        self._logger.info("Downloading {} version of {}".format(version, addon))
        try:
            with ZipFile(BytesIO(self._api.addon(addon, version))) as zip:
                self._wow_helper.install_addon(addon, zip)
        except (ApiTransientError, ApiError) as e:
            # either the user or we will try again later
            self._logger.error("Addon download error: {}".format(str(e)))


    def _set_fsm_state(self, new_state):
        if new_state == self._state:
            # already in the desired state
            return
        old_state = self._state
        self._state = new_state
        if not self.State.is_valid_transition(old_state, new_state):
            raise Exception("Invalid state transtion from {} to {}!".format(old_state, new_state))

        self._logger.info("Set FSM state to {}".format(new_state))
        is_logged_out = (new_state == self.State.LOGGED_OUT)
        # show the ToU if they haven't already accepted them
        if not is_logged_out and not self._settings.accepted_terms:
            self.show_terms.emit()
            self._wait_for_event(self.WaitEvent.TERMS_ACCEPTED)
            self._settings.accepted_terms = True
        if self._is_logged_out is None or self._is_logged_out != is_logged_out:
            self._logger.debug("Changing visibility: {}".format(str(is_logged_out)))
            self.set_main_window_visible.emit(not is_logged_out)
            self.set_login_window_visible.emit(is_logged_out)
            self._is_logged_out = is_logged_out
        if new_state == self.State.LOGGED_OUT:
            if old_state != self.State.INIT:
                self.show_desktop_notification.emit("You've been logged out.", True)
            self._api.logout()
            self.stop_sleeping()
        elif new_state == self.State.PENDING_NEW_SESSION:
            pass
        elif new_state == self.State.VALID_SESSION:
            self.set_main_window_premium_button_visible.emit(not self._api.get_is_premium())
            self._settings.has_beta_access = self._api.get_is_premium() or self._api.get_is_beta()
            self.settings_changed.emit()
            if old_state == self.State.LOGGED_OUT:
                # we just logged in so clean up a few things
                if not self._wow_helper.has_valid_wow_path():
                    self._wow_helper.find_wow_path()
                # reset the login window
                self.set_login_window_enabled.emit(True)
                self.set_login_window_button_text.emit("Login")
                # reset the main window
                self.set_main_window_sync_status_data.emit([])
                self.set_main_window_addon_status_data.emit([])
                self.set_main_window_backup_status_data.emit([])
        elif new_state == self.State.SLEEPING:
            pass
        else:
            raise Exception("Unpexected state transition from {} to {}".format(old_state, new_state))


    def _login_request(self):
        try:
            self._api.login(self._settings.email, self._settings.password)
            # the login was successful!
            self._logger.info("Logged in successfully ({})!".format(self._api.get_username()))
            self._set_fsm_state(self.State.VALID_SESSION)
        except (ApiTransientError, ApiError) as e:
            # either the user or we will try again later
            self._logger.error("Login error: {}".format(str(e)))
            if isinstance(e, ApiError):
                self._settings.email = ""
                self._settings.password = ""
                self._set_fsm_state(self.State.LOGGED_OUT)
            else:
                # try again in 1 minute
                self.sleep(60)
            return str(e)

    def _login(self):
        self.set_login_window_enabled.emit(True)
        self.set_login_window_button_text.emit("Login")
        if self._settings.email == "" or self._settings.password == "":
            # wait for the user to login
            email, password = self._wait_for_event(self.WaitEvent.LOGIN_BUTTON)
            # do a simple sanity check on the email / password provided
            if email and re.match(r"[^@]+@[^@]+\.[^@]+", email) and password != "":
                # this is a valid email and password, so store it
                self._settings.email = email
                self._settings.password = sha512(password.encode("utf-8")).hexdigest()
                self.set_login_window_error_text.emit("")
            else:
                # the email / password is not valid
                self.set_login_window_error_text.emit("Invalid email / password")
        else:
            # send off a login request
            self.set_login_window_enabled.emit(False)
            self.set_login_window_button_text.emit("Logging in...")
            error_msg = self._login_request()
            if error_msg:
                self.set_login_window_error_text.emit(error_msg)


    def _check_status(self):
        try:
            result = self._api.status()
        except (ApiError, ApiTransientError) as e:
            self._logger.error("Got error from status API: {}".format(str(e)))
            return

        self.set_main_window_title.emit("TradeSkillMaster Application r{} - {}".format(Config.CURRENT_VERSION, self._api.get_username()))
        app_info = result['appInfo']
        if app_info['version'] > Config.CURRENT_VERSION:
            # we should have already updated - abort and wait to try again
            return
        elif app_info['news'] != self._last_news:
            # show news
            self.show_desktop_notification.emit(app_info['news'], False)
            self._last_news = app_info['news']

        # update addon status
        self._addon_versions = result['addons']
        self._update_addon_status()

        # download addon updates
        installed_addons = []
        install_all = False
        download_notifications = []
        for addon in self._addon_versions:
            latest_version = addon['betaVersion'] if self._settings.tsm3_beta else addon['version']
            version_type, version_int, version_str = self._wow_helper.get_installed_version(addon['name'])
            if self._settings.tsm3_beta and version_type == WoWHelper.RELEASE_VERSION:
                # upgrade to beta
                version_int = 0
                version_str = ""
                install_all = True
            elif not self._settings.tsm3_beta and version_type == WoWHelper.BETA_VERSION:
                # downgrade to release
                version_int = 0
                version_str = ""
                install_all = True
            elif version_type == WoWHelper.INVALID_VERSION and install_all:
                # install all addons when upgrading / downgrading
                version_int = 0
                version_str = ""
            if version_type in [WoWHelper.RELEASE_VERSION, WoWHelper.BETA_VERSION] or install_all:
                if latest_version == 0:
                    # remove this addon since it no longer exists
                    self._wow_helper.delete_addon(addon['name'])
                elif version_int < latest_version and (self._api.get_is_premium() or self._settings.tsm3_beta):
                    # update this addon
                    self._download_addon(addon['name'], "beta" if self._settings.tsm3_beta else "release")
                    if self._settings.addon_notification:
                        download_notifications.append("Downloaded {} {}".format(addon['name'], self._wow_helper.get_installed_version(addon['name'])[2]))
                    installed_addons.append(addon['name'])
                else:
                    installed_addons.append(addon['name'])
            else:
                # this is a Dev version
                installed_addons.append(addon['name'])
        if len(download_notifications) > 2:
            self.show_desktop_notification.emit("Downloading addon updates!", False)
        else:
            for text in download_notifications:
                self.show_desktop_notification.emit(text, False)
        backed_up_accounts = self._wow_helper.set_addons_and_do_backups(installed_addons)
        if self._settings.backup_notification:
            for account in backed_up_accounts:
                self.show_desktop_notification.emit("Created backup for {}".format(account), False)
        self._update_backup_status()

        # update addon status again incase we changed something (i.e. downloaded updates or deleted an old addon)
        self._update_addon_status()

        # check realm data (AuctionDB / Shopping / WoWuction) status
        app_data = self._wow_helper.get_app_data()
        if not app_data:
            # TSM_AppHelper is not installed
            self.show_desktop_notification.emit("You need to install the TradeSkillMaster_AppHelper addon!", True)
            self.set_main_window_header_text.emit("<font color='red'>You need to install <a href=\"http://www.curse.com/addons/wow/tradeskillmaster_apphelper\">TradeSkillMaster_AppHelper</a>!</font>")
            return
        auctiondb_updates = []
        shopping_updates = []
        wowuction_updates = []
        self._data_sync_status = {}
        if len(result['realms']) == 0:
            # No realms setup so no point in going further
            self.show_desktop_notification.emit("You have no realms setup!", True)
            self.set_main_window_header_text.emit("<font color='red'>You have no <a href=\"https://tradeskillmaster.com/realms\">realms setup</a>!</font>")
            return
        for info in result['realms']:
            self._data_sync_status[info['name']] = {
                'id': info['id'],
                'auctiondb': info['lastModified'] if info['auctiondb'] else 0,
                'shopping': info['lastModified'] if info['name'] != "Global" and self._api.get_is_premium() else 0,
                'wowuction': result['wowuction']['lastModified'] if info['wowuction'] else 0,
            }
        self._update_data_sync_status()
        for realm_name, info in self._data_sync_status.items():
            if info['auctiondb'] > app_data.last_update("AUCTIONDB_MARKET_DATA", realm_name):
                auctiondb_updates.append(info['id'])
            if info['shopping'] > app_data.last_update("SHOPPING_SEARCHES", realm_name):
                shopping_updates.append(info['id'])
            if info['wowuction'] > app_data.last_update("WOWUCTION_MARKET_DATA", realm_name):
                wowuction_updates.append(info['id'])

        hit_error = False
        if auctiondb_updates:
            # get auctiondb updates (all at once)
            try:
                updated_realms = []
                for auctiondb_data in self._api.auctiondb(auctiondb_updates)['data']:
                    for realm_id in auctiondb_data['realms']:
                        realm_name, last_modified = next((x['name'], x['lastModified']) for x in result['realms'] if x['id'] == realm_id)
                        app_data.update("AUCTIONDB_MARKET_DATA", realm_name, auctiondb_data['data'], last_modified)
                        updated_realms.append(realm_name)
                if self._settings.realm_data_notification:
                    self.show_desktop_notification.emit("Updated AuctionDB data for {}".format(" / ".join(updated_realms)), False)
            except (ApiError, ApiTransientError) as e:
                # log an error and keep going
                self._logger.error("Got error from AuctionDB API: {}".format(str(e)))
                hit_error = True
        if shopping_updates:
            # get shopping updates (all at once)
            try:
                updated_realms = []
                for shopping_data in self._api.shopping(shopping_updates)['data']:
                    for realm_id in shopping_data['realms']:
                        realm_name, last_modified = next((x['name'], x['lastModified']) for x in result['realms'] if x['id'] == realm_id)
                        app_data.update("SHOPPING_SEARCHES", realm_name, shopping_data['data'], last_modified, True)
                        updated_realms.append(realm_name)
                if self._settings.realm_data_notification and updated_realms:
                    self.show_desktop_notification.emit("Updated Great Deals for {}".format(" / ".join(updated_realms)), False)
            except (ApiError, ApiTransientError) as e:
                # log an error and keep going
                self._logger.error("Got error from Shopping API: {}".format(str(e)))
                hit_error = True
        if wowuction_updates:
            # get wowuction updates
            try:
                updated_realms = []
                for realm_id in wowuction_updates:
                    realm_name, realm_slug = next((x['name'], x['slug']) for x in result['realms'] if x['id'] == realm_id)
                    last_modified = result['wowuction']['lastModified']
                    if realm_name == "Global":
                        raw_data = self._api.wowuction()
                        data = raw_data['regionData']
                    else:
                        raw_data = self._api.wowuction(realm_slug)
                        data = raw_data['realmData']
                    fields = ["\"{}\"".format(x) for x in data['fields']]
                    data = data['horde']
                    # time for some beautiful python goodness...this basically just converts a python list of lists into a stringified lua list of lists
                    data = "{{{}}}".format(",".join(["{{{}}}".format(",".join([str(x) for x in item])) for item in data]))
                    processed_data = "{{downloadTime={},fields={{{}}},data={}}}".format(last_modified, ",".join(fields), data)
                    app_data.update("WOWUCTION_MARKET_DATA", realm_name, processed_data, last_modified)
                    updated_realms.append(realm_name)
                if self._settings.realm_data_notification:
                    self.show_desktop_notification.emit("Updated WoWuction data for {}".format(" / ".join(updated_realms)), False)
            except (ApiError, ApiTransientError) as e:
                # log an error and keep going
                self._logger.error("Got error from WoWuction API: {}".format(str(e)))
                hit_error = True
        app_data.update("APP_INFO", "Global", "{{version={}}}".format(Config.CURRENT_VERSION), int(time()))
        app_data.save()
        self._update_data_sync_status()
        if not hit_error:
            self.set_main_window_header_text.emit("{}\nEverything is up to date as of {}.".format(app_info['news'], QDateTime.currentDateTime().toString(Qt.SystemLocaleShortDate)))


    def _update_addon_status(self):
        # check addon versions
        addon_status = []
        for addon in self._addon_versions:
            name = addon['name']
            latest_version = addon['betaVersion'] if self._settings.tsm3_beta else addon['version']
            version_type, version_int, version_str = self._wow_helper.get_installed_version(name)
            status = None
            if version_type == WoWHelper.INVALID_VERSION:
                if latest_version == 0:
                    # this addon doesn't exist
                    continue
                status = {'text': "Not installed (double-click to install)", 'click_key':"addon~{}~{}".format(name, "beta" if self._settings.tsm3_beta else "release")}
            elif version_type in [WoWHelper.RELEASE_VERSION, WoWHelper.BETA_VERSION]:
                if latest_version == 0:
                    # this addon no longer exists, so it will be uninstalled
                    status = {'text': "Removing..."}
                elif version_int < latest_version:
                    # this addon needs to be updated
                    if self._api.get_is_premium() or self._settings.tsm3_beta:
                        # defer the auto-updating until after we set the status
                        status = {'text': "Updating..."}
                    else:
                        status = {'text': "Update available. Go premium for auto-updates.", 'color':[255, 0, 0]}
                else:
                    status = {'text': "Up to date"}
            elif version_type == WoWHelper.DEV_VERSION:
                status = {'text': "Automatic updates disabled"}
            else:
                raise Exception("Unexpected version type for {} ({}): {}".format(addon['name'], version_str, version_type))
            if status:
                addon_status.append([{'text': name.replace("TradeSkillMaster_", "TSM_"), 'sort': name}, {'text': version_str}, status])
        self.set_main_window_addon_status_data.emit(addon_status)


    def _update_data_sync_status(self):
        app_data = self._wow_helper.get_app_data()
        if not app_data:
            self.set_main_window_sync_status_data.emit([])
            return
        # check data sync status versions
        sync_status = []
        for realm_name, info in self._data_sync_status.items():
            if info['auctiondb'] == 0:
                # they don't have AuctionDB data enabled for this realm
                auctiondb_status = {'text': "Disabled"}
            elif info['auctiondb'] > app_data.last_update("AUCTIONDB_MARKET_DATA", realm_name):
                # an update is pending
                auctiondb_status = {'text': "Updating..."}
            else:
                auctiondb_status = {'text': "Up to date"}
            if info['wowuction'] == 0:
                # they don't have WoWuction data enabled for this realm
                wowuction_status = {'text': "Disabled"}
            elif info['wowuction'] > app_data.last_update("WOWUCTION_MARKET_DATA", realm_name):
                # an update is pending
                wowuction_status = {'text': "Updating..."}
            else:
                wowuction_status = {'text': "Up to date"}
            if info['shopping'] == 0:
                # they aren't premium so don't get shopping data
                shopping_status = {'text': "N/A"} if realm_name == "Global" else {'text': "Go premium to enabled"}
            elif info['shopping'] > app_data.last_update("SHOPPING_SEARCHES", realm_name):
                # an update is pending
                shopping_status = {'text': "Updating..."}
            else:
                shopping_status = {'text': "Up to date"}
            sync_status.append([{'text': realm_name}, auctiondb_status, wowuction_status, shopping_status])
        self.set_main_window_sync_status_data.emit(sync_status)


    def _update_backup_status(self):
        backup_status = []
        for info in self._wow_helper.get_backups():
            time_info = {'text': info['timestamp'].strftime("%c"), 'sort': int(info['timestamp'].timestamp())}
            assert("~" not in info['account'])
            notes_info = {'text': "Double-click to restore", 'click_key':"backup~{}~{}".format(info['account'], info['timestamp'].strftime(Config.BACKUP_TIME_FORMAT))}
            backup_status.append([{'text': info['account']}, time_info, notes_info])
        self.set_main_window_backup_status_data.emit(backup_status)


    def _upload_data(self):
        # upload black market data
        for key, data in self._wow_helper.get_black_market_data().items():
            region, realm = key
            try:
                if self._api.black_market(region, realm, data, data['updateTime']):
                    self._logger.info("Uploaded black market data ({}, {})!".format(region, realm))
            except (ApiError, ApiTransientError) as e:
                self._logger.error("Got error from black market API: {}".format(str(e)))

        # upload sales data
        for key, data in self._wow_helper.get_accounting_data().items():
            region, realm, account = key
            try:
                last_upload = self._api.sales(region, realm, account)
                if last_upload < data['updateTime']:
                    new_data = []
                    for item_id, sales in data['data'].items():
                        new_data.extend([[item_id] + x for x in sales if x[4] > last_upload])
                    if new_data:
                        # upload the new data
                        self._api.sales(region, realm, account, new_data)
                        self._logger.info("Uploaded sales data ({}, {}, {})!".format(region, realm, account))
            except (ApiError, ApiTransientError) as e:
                self._logger.error("Got error from sales API: {}".format(str(e)))

        # upload group data
        for key, data in self._wow_helper.get_group_data().items():
            account, profile = key
            try:
                if self._api.groups(account, profile, data, data['updateTime']):
                    self._logger.info("Uploaded group data ({}, {})!".format(account, profile))
            except (ApiError, ApiTransientError) as e:
                self._logger.error("Got error from group API: {}".format(str(e)))


    def _get_file_md5(self, path):
        with open(path, "rb") as f:
            return md5(f.read()).hexdigest()


    def _update_app(self):
        # TODO: this won't work on mac
        # don't try to update if we're not frozen
        if not getattr(sys, 'frozen', False):
            return

        base_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), os.pardir))
        os.chdir(base_path)
        app_path = os.path.join(base_path, "app")

        # create a manifest (look table of path -> hash) for the current app files
        app_file_md5 = {}
        for root_path, _, files in os.walk(app_path):
            root_path = os.path.relpath(root_path, app_path)
            for file_name in files:
                path = file_name if root_path == "." else os.path.join(root_path, file_name).replace("\\", "/")
                app_file_md5[path] = self._get_file_md5(os.path.join(app_path, path))

        # grab the latest manifest
        try:
            new_app_files = self._api.app()['files']
        except (ApiError, ApiTransientError) as e:
            self._logger.error("Got error from app API: {}".format(str(e)))
            return

        # create the app_new folder - copy files that haven't changed and download files which have
        app_new_path = os.path.join(base_path, "app_new")
        copy_file_list = []
        download_file_list = []
        if os.path.exists(app_new_path):
            shutil.rmtree(app_new_path)
        for file_info in new_app_files:
            file_path = file_info['path']
            dst_path = os.path.join(app_new_path, file_path)
            if file_info['md5'] == app_file_md5[file_path]:
                # this file hasn't changed so just copy it
                copy_file_list.append((os.path.join(app_path, file_path), dst_path))
            else:
                # we need to download this file
                download_file_list.append((file_path, dst_path))
        if not download_file_list:
            # nothing to update, so bail
            self._logger.warn("There were no new files to download for the update.")
            return
        # copy the files
        for src, dst in copy_file_list:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
        # download the necesary files
        for file_path, dst in download_file_list:
            try:
                with open(dst, 'wb') as f:
                    f.write(self._api.app(file_path))
                self._logger.info("Downloaded file: {}".format(dst))
            except (ApiTransientError, ApiError) as e:
                # abort - we'll try again later
                self._logger.error("App file download error: {}".format(str(e)))
                return
        self.run_updater.emit()
        # assert(False) # we should never get here!


    def _run_fsm(self):
        self._sleep_time = 0
        if self._state == self.State.INIT:
            # just go to the next state - this is so we can show the login window when we enter LOGGED_OUT
            self._set_fsm_state(self.State.LOGGED_OUT)
        elif self._state == self.State.LOGGED_OUT:
            # process login requests (which will move us to VALID_SESSION)
            self._login()
        elif self._state == self.State.PENDING_NEW_SESSION:
            # get a new session by making a login request (which will move us to VALID_SESSION)
            if self._login_request():
                # we failed to login, wait before trying again
                self._sleep_time = Config.STATUS_CHECK_INTERVAL_S
        elif self._state == self.State.VALID_SESSION:
            self._sleep_time = Config.STATUS_CHECK_INTERVAL_S
            self._update_app()
            if not self._wow_helper.has_valid_wow_path():
                self.show_desktop_notification.emit("You need to select your WoW directory in the settings!", True)
                self.set_main_window_header_text.emit("<font color='red'>You need to select your WoW directory in the settings!</font>")
            else:
                # make a status request
                self._check_status()
                # update the accounting tab
                self.set_main_window_accounting_accounts.emit(self._wow_helper.get_accounting_accounts())
                # upload app data
                self._upload_data()
            self._set_fsm_state(self.State.SLEEPING)
        elif self._state == self.State.SLEEPING:
            # go back to PENDING_NEW_SESSION
            self._set_fsm_state(self.State.PENDING_NEW_SESSION)
        else:
            raise Exception("Invalid state {}".format(self._state))
        while self._sleep_time > 0:
            self._sleep_time -= 1
            self.sleep(1)


    def run(self):
        try:
            while True:
                self._run_fsm()
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            self._logger.error("".join(lines))
            raise
