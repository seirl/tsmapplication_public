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


# General python modules
import sys
import os
import traceback
import logging
from logging.handlers import RotatingFileHandler

# PyQt5
from PyQt5.QtWidgets import QMainWindow, QApplication

# Local modules
from ui.MainWindow import MainWindow


if __name__ == "__main__":
    # initialize the logger
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s", datefmt="%m/%d/%Y %H:%M:%S")
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = RotatingFileHandler("TSMApplication.log", mode='w', maxBytes=200000, backupCount=1)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s", "%m/%d/%Y %H:%M:%S"))
    handler.doRollover() # clear the log everytime we start
    logger.addHandler(handler)

    # here we go!
    logger.info("Starting TSM Application")
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sync_status = [
        ('US Region', 'Updated 2 minutes ago', 'Updated 14 hours ago', 'Updated 2 minutes ago'),
        ('Tichondrius', 'Updated 2 minutes ago', 'Updated 14 hours ago', 'Updated 2 minutes ago'),
        ('Dunemaul', 'Updated 2 minutes ago', 'Updated 14 hours ago', 'Updated 2 minutes ago'),
        ('Chromaggus', 'Updated 2 minutes ago', 'Updated 14 hours ago', 'Updated 2 minutes ago'),
        ('Illidan', 'Updated 2 minutes ago', 'Updated 14 hours ago', 'Updated 2 minutes ago'),
    ]
    main_window.set_sync_status_data(sync_status)
    addon_versions = [
        ('TradeSkillMaster', '3X205', 'Up to date'),
        ('TradeSkillMaster_Accounting', '3X30', 'Up to date'),
        ('TradeSkillMaster_AppHelper', '3X4', 'Up to date'),
        ('TradeSkillMaster_AuctionDB', '3X10', 'Up to date'),
        ('TradeSkillMaster_Auctioning', '3X84', 'Up to date'),
        ('TradeSkillMaster_Crafting', '3X91', 'Up to date'),
        ('TradeSkillMaster_Destroying', '3X27', 'Up to date'),
        ('TradeSkillMaster_Mailing', '3X42', 'Up to date'),
        ('TradeSkillMaster_Shopping', '3X68', 'Up to date'),
        ('TradeSkillMaster_Vendoring', '3X46', 'Up to date'),
        ('TradeSkillMaster_Warehousing', '3X14', 'Up to date'),
        ('TradeSkillMaster_WoWuction', '3X5', 'Up to date'),
    ]
    main_window.set_addon_status_data(addon_versions)

    # Catch and log any exceptions that occur while running the event loop (before exiting)
    try:
        app.exec_()
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        logger.error("".join(lines))