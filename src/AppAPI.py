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
import PrivateConfig

# General python modules
from base64 import b64encode
from hashlib import md5, sha1, sha256, sha512
from gzip import GzipFile
from io import BytesIO, StringIO
import http
import json
import logging
import socket
from time import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


_DEFAULT_USER_INFO = {
    'session': "",
    'userId': 0,
    'name': "",
    'isBeta': False,
    'isPremium': False,
    'wowuction': None,
}


class ApiError(Exception):
    # raised when an api request fails and the server returns an error message
    pass


class ApiTransientError(Exception):
    # raised when we get an unexpected response from the server (and should generally just try again later)
    def __init__(self, message="Failed to connect to the server"):
        Exception.__init__(self, message)


class AppAPI:
    def __init__(self):
        self._last_login = 0
        self._user_info = _DEFAULT_USER_INFO.copy()
        socket.setdefaulttimeout(30)


    def _make_request(self, *args, **kwargs):
        data = kwargs.pop('data', None)
        alt_url = kwargs.pop('alt_url', None)
        assert(not kwargs)
        headers = {
            'Accept-Encoding': 'gzip',
        }
        if data:
            if type(data) == str:
                headers['Content-Type'] = "text/plain"
            elif type(data) in [list, dict]:
                data = json.dumps(data)
                headers['Content-Type'] = "application/json"
            else:
                raise Exception("Invalid data type ({})!".format(type(data)))
            # gzip the data
            buffer = BytesIO()
            with GzipFile(fileobj=buffer, mode="wb") as f:
                f.write(bytes(data, 'UTF-8'))
            data = buffer.getvalue()
            headers['Content-Encoding'] = "gzip"
        current_time = int(time())
        if alt_url:
            url = alt_url
        else:
            query_params = {
                'session': self._user_info['session'],
                'version': Config.CURRENT_VERSION,
                'time': current_time,
                'token': sha256("{}:{}:{}".format(Config.CURRENT_VERSION, current_time, PrivateConfig.get_token_salt()).encode("utf-8")).hexdigest()
            }
            url = "{}/{}?{}".format(Config.APP_API_BASE_URL, "/".join(args), urlencode(query_params))
        logger = logging.getLogger()
        logger.debug("Making request: {}".format(url))
        try:
            with urlopen(Request(url, headers=headers, data=data)) as response:
                content_type = response.info().get_content_type()
                raw_data = response.read()
                if response.info().get("Content-Encoding") == "gzip":
                    with GzipFile(fileobj=BytesIO(raw_data), mode="rb") as f:
                        raw_data = f.read()
                if alt_url and content_type == "text/plain":
                    # wowuction doesn't set the content type header correctly
                    raw_data = raw_data.decode(response.info().get_param("charset", "utf-8"))
                    try:
                        return json.loads(raw_data)
                    except ValueError:
                        # it was probably an error
                        raise ApiTransientError()
                elif content_type == "application/zip" or content_type == "application/octet-stream":
                    return raw_data
                elif content_type == "application/json":
                    raw_data = raw_data.decode(response.info().get_param("charset", "utf-8"))
                    data = json.loads(raw_data)
                    if not data:
                        # the data is invalid
                        logger.error("Invalid data: '{}'".format(raw_data))
                        raise ApiTransientError()
                    elif not alt_url and not data.pop("success", False):
                        # this request failed and we got an error back
                        raise ApiError(data['error'])
                    # this request was successful
                    return data
        except Exception as e:
            # the request failed (weren't able to connect to the server)
            if isinstance(e, ApiError) or isinstance(e, ApiTransientError):
                raise
            if isinstance(e, HTTPError):
                logger.error("Got HTTP status code of {} ({})".format(e.code, e.reason))
            elif isinstance(e, URLError):
                logger.error("Error while making HTTP request ({})".format(e.reason))
            else:
                logger.error("Error while making HTTP request ({})".format(str(e)))
        raise ApiTransientError()


    def get_username(self):
        return self._user_info['name']


    def get_is_beta(self):
        return self._user_info['isBeta']


    def get_is_premium(self):
        return self._user_info['isPremium']


    def logout(self):
        self._user_info = _DEFAULT_USER_INFO


    def login(self, email, password):
        email_hash = sha256(email.lower().encode("utf-8")).hexdigest()
        password_hash = sha512((password + PrivateConfig.get_password_salt()).encode("utf-8")).hexdigest()
        self._user_info = self._make_request("login", email_hash, password_hash)
        self._last_login = time()


    def status(self):
        result = self._make_request("status")
        self._user_info['wowuction'] = {}
        self._user_info['wowuction']['region'] = result['wowuction']['region']
        self._user_info['wowuction']['token'] = result['wowuction']['token']
        self._user_info['wowuction']['tokenTime'] = result['wowuction']['tokenTime']
        return result


    def addon(self, name, version):
        return self._make_request("addon", name, version)


    def auctiondb(self, realm_ids):
        return self._make_request("auctiondb", "-".join([str(x) for x in realm_ids]))


    def shopping(self, realm_ids):
        return self._make_request("shopping", "-".join([str(x) for x in realm_ids]))


    def wowuction(self, realm_slug=None):
        if realm_slug:
            # realm data
            params = [self._user_info['wowuction']['region'], realm_slug, self._user_info['wowuction']['token'], self._user_info['wowuction']['tokenTime'], self._user_info['userId']]
            url = "http://www.wowuction.com/{}/{}/horde/Tools/GetTSMDataStatic?token={}&app=tsm&version=4&realmdata=true&regiondata=false&time={}&tsmuserid={}".format(*params)
        else:
            # region data
            params = [self._user_info['wowuction']['region'], self._user_info['wowuction']['token'], self._user_info['wowuction']['tokenTime'], self._user_info['userId']]
            url = "http://www.wowuction.com/{}/aegwynn/horde/Tools/GetTSMDataStatic?token={}&app=tsm&version=4&realmdata=false&regiondata=true&time={}&tsmuserid={}".format(*params)
        return self._make_request(alt_url=url)


    def log(self, data, is_crash=False):
        self._make_request("log", "crash" if is_crash else "user", data=data)


    def black_market(self, region, realm, data, update_time):
        realm = b64encode(realm.encode("utf8")).decode("ascii")
        # first, get the last upload time
        last_upload = self._make_request("black_market", region, realm)['lastUpload']
        if update_time > last_upload:
            # this data is newer than what's on the server, so upload it
            self._make_request("black_market", region, realm, data=data)
            return True
        return False


    def sales(self, region, realm, account, data=None):
        realm = b64encode(realm.encode("utf8")).decode("ascii")
        account = b64encode(account.encode("utf8")).decode("ascii")
        if data:
            # upload the data
            self._make_request("sales", region, realm, account, data=data)
        else:
            # get the last upload time
            return self._make_request("sales", region, realm, account)['lastUpload']


    def groups(self, account, profile, data, update_time):
        account = b64encode(account.encode("utf8")).decode("ascii")
        profile = b64encode(profile.encode("utf8")).decode("ascii")
        # first, get the last upload time
        last_upload = self._make_request("groups", account, profile)['lastUpload']
        if update_time > last_upload:
            # this data is newer than what's on the server, so upload it
            self._make_request("groups", account, profile, data=data)
            return True
        return False


    def app(self, path=None):
        if path:
            path = b64encode(path.encode("utf8")).decode("ascii")
            return self._make_request("app", "win" if Config.IS_WINDOWS else "mac", path)
        else:
            return self._make_request("app", "win" if Config.IS_WINDOWS else "mac")
