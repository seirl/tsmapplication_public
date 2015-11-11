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


# PyQt5
from PyQt5.QtCore import pyqtSignal, QAbstractTableModel, Qt
from PyQt5.QtGui import QBrush, QColor


class TableModel(QAbstractTableModel):
    def __init__(self, parent, header, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self._header = header
        self._info = []


    def rowCount(self, parent):
        return len(self._info)


    def columnCount(self, parent):
        return len(self._header)


    def data(self, index, role):
        if not index.isValid():
            return None
        cell_info = self._info[index.row()][index.column()]
        if role == Qt.DisplayRole:
            # return the text to be displayed
            return cell_info['text']
        elif role == Qt.ForegroundRole:
            return QBrush(QColor(*cell_info['color']))
        return None


    def headerData(self, col, orientation, role):
        if orientation != Qt.Horizontal:
            return None
        if role == Qt.DisplayRole:
            return self._header[col]
        return None


    def set_info(self, info):
        self.beginResetModel()
        # set defaults
        for row in info:
            temp_row = []
            assert(len(row) == len(self._header))
            for cell_info in row:
                # put spaces around text
                cell_info['text'] = " {} ".format(cell_info['text'])
                if 'color' not in cell_info:
                    cell_info['color'] = [255, 255, 255]
                if 'click_enabled' not in cell_info:
                    cell_info['click_enabled'] = False
                elif cell_info['click_enabled']:
                    assert(cell_info['click_key'])
        self._info = info
        self.endResetModel()
        return True


    def get_click_key(self, index):
        if not index.isValid() or not self._info[index.row()][index.column()]['click_enabled']:
            return None
        return self._info[index.row()][index.column()]['click_key']


    def sort(self, col, order):
        self.beginResetModel()
        self.layoutAboutToBeChanged.emit()
        self._info = sorted(self._info, key=lambda info: info[col]['text'])        
        if order == Qt.DescendingOrder:
            self._info.reverse()
        self.endResetModel()
