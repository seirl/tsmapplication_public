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
from zipfile import ZipFile, ZIP_DEFLATED


# a list of all supported operations
SUPPORTED_OPERATIONS = ["clean", "build", "run", "package"]

# what operations to run by default
DEFAULT_OPERATIONS = ["clean", "build", "run"]

# folders where to look for source files
PYTHON_SRC_PATH = "src"
RESOURCE_SRC_PATH = "resources"
UI_SRC_PATH = "ui"

# folder to compile into
BUILD_DIR = "build"

# folder to build the exe / dlls into
DIST_DIR = "build/dist"

# name of the main script to run
MAIN_SCRIPT = "main.py"

# name of the .exe and .zip that are built
APP_NAME = "TSMApplication"


def find_files(dir, pattern):
    for root_path, _, file_names in os.walk(dir):
        for file_name in fnmatch.filter(file_names, pattern):
            yield os.path.join(root_path, file_name)

            
class Operations:
    @staticmethod
    def __dir__():
        return ['clean', 'build', 'run', 'package']

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
        os.system("{} {} --debug".format(sys.executable, os.path.join(BUILD_DIR, MAIN_SCRIPT)))

    @staticmethod
    def package():
        from setuptools import setup
        sys.path.append("build/")

        # setuptools uses argv, so we'll just fake it
        sys.argv = ["make.py"]
        if sys.platform.startswith("win32"):
            import site
            import py2exe
            sys.argv.append("py2exe")

            setup(
                windows = [
                    {
                        "script": os.path.join(BUILD_DIR, MAIN_SCRIPT),
                        "icon_resources": [(1, os.path.join(RESOURCE_SRC_PATH, "logo.ico"))],
                        "dest_base" : APP_NAME
                    }
                ],
                data_files = [("platforms", [os.path.join(next(x for x in site.getsitepackages() if "site-packages" in x), "PyQt5/plugins/platforms/qwindows.dll")])],
                options = {
                    'py2exe': {
                        'includes': ["sip"],
                        'dist_dir': DIST_DIR,
                        'excludes': ["_ssl", 'pydoc', 'doctest', 'test'],
                        'bundle_files': 2,
                        'compressed': True,
                    }
                },
            )

            # manually copy some dlls we've pre-built
            dll_prebuilt = ["icudt53.dll"]
            for dll in dll_prebuilt:
                src_path = os.path.join(RESOURCE_SRC_PATH, dll)
                dst_path = os.path.join(DIST_DIR, dll)
                if os.path.isfile(src_path):
                    print("Copy DLL {} to {}".format(src_path, dst_path))
                    shutil.copy(src_path, dst_path)
        elif sys.platform.startswith("darwin"):
            import py2app
            sys.argv.append("py2app")

            setup(
                app = os.path.join(BUILD_DIR, MAIN_SCRIPT),
                options = {
                    'py2app': {
                        'argv_emulation': True,
                        'includes': ["sip", "PyQt5"],
                        # 'dist_dir': DIST_DIR,
                        # 'excludes': ["_ssl", 'pydoc', 'doctest', 'test'],
                        # 'compressed': True,
                    }
                },
                setup_requires = ['py2app'],
            )
        else:
            raise Exception("Unsupported platform!")

        # zip up the result
        zip_path = os.path.join(BUILD_DIR, "{}.zip".format(APP_NAME))
        print("Creating zip: {}".format(zip_path))
        with ZipFile(zip_path, 'w', ZIP_DEFLATED) as zip:
            for path in os.listdir(DIST_DIR):
                abs_path = os.path.abspath(os.path.join(DIST_DIR, path))
                if os.path.isdir(abs_path):
                    for sub_path in os.listdir(abs_path):
                        abs_sub_path = os.path.abspath(os.path.join(abs_path, sub_path))
                        assert(os.path.isfile(abs_sub_path))
                        zip.write(abs_sub_path, os.path.join(path, os.path.basename(sub_path)))
                else:
                    zip.write(abs_path, os.path.basename(path))
        shutil.rmtree(DIST_DIR)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", nargs="*", default=DEFAULT_OPERATIONS,
                        help="Specifies which operation(s) to perform. If not specified, will run '{}'. Supported operations are {}"
                             .format(" ".join(DEFAULT_OPERATIONS), ", ".join(["'{}'".format(x) for x in SUPPORTED_OPERATIONS])))
    args = parser.parse_args()
    # check that all the operations are valid (cause argparse can't easily do this for us in this case)
    for op in args.operation:
        if op not in SUPPORTED_OPERATIONS:
            print("Invalid operation: {}".format(op))
            sys.exit(1)

    # cd into the base directory (where this script lives)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # run each of the operations
    for op in args.operation:
        print("Executing '{}'...".format(op))
        getattr(Operations, op)()
