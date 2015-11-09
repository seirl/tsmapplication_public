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
from PyQt5 import uic

# General python modules
import argparse
import fnmatch
import os
import sys
import shutil


# what commands to run by default
DEFAULT_OPERATIONS = ["clean", "build", "run"]

# folders where to look for source files
PYTHON_SRC_PATH = "src"
RESOURCE_SRC_PATH = "resources"
UI_SRC_PATH = "ui"

# folder to compile into
BUILD_DIR = "build"

# name of the main script to run
MAIN_SCRIPT = "main.py"


def find_files(dir, pattern):
    for root_path, _, file_names in os.walk(dir):
        for file_name in fnmatch.filter(file_names, pattern):
            yield os.path.join(root_path, file_name)

            
class Operations:
    @staticmethod
    def clean():
        # delete the build directory
        if os.path.exists(BUILD_DIR):
            shutil.rmtree(BUILD_DIR)

    @staticmethod
    def build():
        # copy all the python files into the build directory
        for path in find_files(PYTHON_SRC_PATH, "*.py"):
            build_file_path = os.path.join(BUILD_DIR, os.path.relpath(path, PYTHON_SRC_PATH))
            if not os.path.exists(os.path.dirname(build_file_path)):
                os.makedirs(os.path.dirname(build_file_path))
            shutil.copy(path, build_file_path)

        # compile the resource files
        for path in find_files(RESOURCE_SRC_PATH, "*.qrc"):
            built_file_path = os.path.join(BUILD_DIR, "{}_rc.py".format(os.path.splitext(os.path.basename(path))[0]))
            if os.system("pyrcc5 {} -o {}".format(path, built_file_path)) != 0:
                print("Failed to compile resource: {}".format(path))
                sys.exit(1)

        # compile the UI files
        for path in find_files(UI_SRC_PATH, "*.ui"):
            built_file_path = os.path.join(BUILD_DIR, "{}_ui.py".format(os.path.splitext(os.path.basename(path))[0]))
            with open(built_file_path, 'w') as py_file:
                uic.compileUi(path, py_file)

    @staticmethod
    def run():
        os.system("python {}".format(os.path.join(BUILD_DIR, MAIN_SCRIPT)))

    @staticmethod
    def package():
        from py2exe.build_exe import py2exe
        from distutils.core import setup
        setup(windows=[{"script": os.path.join(BUILD_DIR, MAIN_SCRIPT)}])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", nargs="*", default=DEFAULT_OPERATIONS,
                        help="Specifies which operation(s) to perform. If not specified, will run 'clean build run'.")
    args = parser.parse_args()
    # check that all the operations are valid (cause argparse can't easily do this for us in this case)
    for op in args.operation:
        try:
            getattr(Operations, op)
        except AttributeError:
            print("Invalid operation: {}".format(op))
            sys.exit(1)

    # cd into the base directory (where this script lives)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # run each of the operations
    for op in args.operation:
        print("Executing '{}'...".format(op))
        getattr(Operations, op)()
