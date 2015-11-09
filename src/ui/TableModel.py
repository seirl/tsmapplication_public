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
from PyQt5.QtCore import QAbstractTableModel, Qt
from PyQt5.QtGui import QBrush, QColor, QFont

# General python modules
from operator import itemgetter


class TableModel(QAbstractTableModel):
    def __init__(self, parent, header, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self._data = []
        self._header = header


    def rowCount(self, parent):
        return len(self._data)


    def columnCount(self, parent):
        return len(self._header)


    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            # return the text to be displayed
            return self._data[index.row()][index.column()]
        return None


    def headerData(self, col, orientation, role):
        if orientation != Qt.Horizontal:
            return None
        if role == Qt.DisplayRole:
            return self._header[col]
        return None


    def setData(self, data):
        self.beginResetModel()
        self._data = []
        for row in data:
            temp_row = []
            if len(row) != len(self._header):
                raise Exception("Invalid data!")
            for cell in row:
                # put spaces around cell contents
                temp_row.append(" {} ".format(cell))
            self._data.append(temp_row)
        self.endResetModel()
        return True


    def sort(self, col, order):
        self.beginResetModel()
        self.layoutAboutToBeChanged.emit()
        self._data = sorted(self._data, key=itemgetter(col))        
        if order == Qt.DescendingOrder:
            self._data.reverse()
        self.endResetModel()
