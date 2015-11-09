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


from PyQt5.QtCore import QObject, QSettings, pyqtProperty, pyqtSignal
from itertools import starmap


def load_settings(items, *args, **kargs):
    class Settings(QObject):
        def __init__(self):
            super(Settings, self).__init__()
            self.settings = QSettings(*args, **kargs)

    def init_item(key, default):
        def get(self):
            return self.settings.value(key, default)
        get.__name__ = key

        def set(self, value):
            if getattr(self, key) == value:
                return
            self.settings.setValue(key, value)
            getattr(self, "{}_changed".format(key)).emit(value)
        set.__name__ = "set_{}".format(key)
        
        class SignalWrapper(QObject):
            signal = pyqtSignal(type(default))
            def emit(self, value):
                return self.signal.emit(value)

            def connect(self, slot):
                return self.signal.connect(slot)

        key = key.replace("/", "_")
        setattr(Settings, key, pyqtProperty(type(default), get, set))
        setattr(Settings, "{}_changed".format(key), SignalWrapper())
        setattr(Settings, "set_{}".format(key), set)
        setattr(Settings, "set_{}".format(key), getattr(Settings, "set_{}".format(key)))

    for key, default in items.items():
        init_item(key, default)

    return Settings()
