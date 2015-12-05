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
from importlib import import_module
import os
import shutil
import sys
from zipfile import ZipFile, ZIP_DEFLATED


# a list of all supported operations
SUPPORTED_OPERATIONS = ["clean", "build", "run", "dist_win", "dist_mac"]

# what operations to run by default
DEFAULT_OPERATIONS = ["clean", "build", "run"]

# folders where to look for source files
PYTHON_SRC_PATH = "src"
RESOURCE_SRC_PATH = "resources"
UI_SRC_PATH = "ui"

# folder to compile into
BUILD_DIR = "build"

# folder to build the app exe / dlls into
APP_DIST_DIR = "build/app"

# folder to build the updater exe / dlls into
UPDATER_DIST_DIR = "build/updater"

# name of the main script to run
MAIN_SCRIPT = "main.py"

# name of the main script to run for the updater
UDPATER_MAIN_SCRIPT_PATH = "updater/main.py"

# name of the app's .exe and .zip that are built
APP_NAME = "TSMApplication"

# name of the updater's .exe and .zip that are built
UPDATER_NAME = "TSMUpdater"

# path inno setup's ISCC.exe file (for dist_win)
ISCC_PATH = "\"C:\\Program Files (x86)\\Inno Setup 5\\ISCC.exe\""

# template for resource script which loads a compressed resource file
RESOURCE_CODE = """
# WARNING: This code is generated. All changes made in this file will be lost!

import os
import sys

rel_path = "{}"
if getattr(sys, 'frozen', False):
    _resource_data_path = os.path.join(os.path.dirname(sys.executable), rel_path)
else:
    _resource_data_path = os.path.join(os.path.dirname(sys.argv[0]), rel_path)
with open(_resource_data_path, "rb") as f:
    def get_length():
        return (2 ** 24) * ord(f.read(1)) + (2 ** 16) * ord(f.read(1)) + (2 ** 8) * ord(f.read(1)) + ord(f.read(1))
    struct_len = get_length()
    name_len = get_length()
    data_len = get_length()
    import os
    assert(os.path.getsize(_resource_data_path) == (struct_len + name_len + data_len + 12))
    qt_resource_struct = f.read(struct_len)
    qt_resource_name = f.read(name_len)
    qt_resource_data = f.read(data_len)

assert(len(qt_resource_struct) > 0 and len(qt_resource_name) > 0 and len(qt_resource_data) > 0)

from PyQt5 import QtCore
def qInitResources():
    QtCore.qRegisterResourceData(0x01, qt_resource_struct, qt_resource_name, qt_resource_data)
def qCleanupResources():
    QtCore.qUnregisterResourceData(0x01, qt_resource_struct, qt_resource_name, qt_resource_data)
qInitResources()
"""

# template for Inno Setup script
INNO_SETUP_CODE = r"""
#define MyAppName "TradeSkillMaster Application"
#define MyExeName "TSMApplication"

[Setup]
AppId={{c44da794-b956-4d50-8733-346d56ae63c7}
AppName={#MyAppName}
AppPublisher=TradeSkillMaster
AppPublisherURL=http://www.tradeskillmaster.com/
AppVersion=1.0
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\app\{#MyExeName}.exe
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
DisableProgramGroupPage=yes

[Dirs]
Name: "{app}"; Permissions: Users-full
Name: "{app}\app"; Permissions: Users-full
Name: "{app}\app\imageformats"; Permissions: Users-full
Name: "{app}\app\platforms"; Permissions: Users-full
Name: "{app}\updater"; Permissions: Users-full

[Files]
%s

[Icons]
Name: "{group}\{#MyExeName}"; Filename: "{app}\app\{#MyExeName}.exe"
Name: "{group}\TradeSkillMaster.com"; Filename: "http://www.tradeskillmaster.com/"
Name: "{commondesktop}\{#MyExeName}"; Filename: "{app}\app\{#MyExeName}.exe"

[Code]
 procedure CurUninstallStepChanged (CurUninstallStep: TUninstallStep);
 var
     mres : integer;
 begin
    case CurUninstallStep of
      usPostUninstall:
        begin
          mres := MsgBox('Do you want to remove the settings?', mbConfirmation, MB_YESNO or MB_DEFBUTTON2)
          if mres = IDYES then
            DelTree(ExpandConstant('{userappdata}\TradeSkillMaster'), True, True, True);
            RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER, 'SOFTWARE\TradeSkillMaster');
       end;
   end;
end;

function GetUninstallString: string;
var
  sUnInstPath: string;
  sUnInstallString: String;
begin
  Result := '';
  sUnInstPath :=  ExpandConstant('Software\Microsoft\Windows\CurrentVersion\Uninstall\{#emit SetupSetting("AppID")}_is1'); //Your App GUID/ID
  sUnInstallString := '';
  if not RegQueryStringValue(HKLM, sUnInstPath, 'UninstallString', sUnInstallString) then
    RegQueryStringValue(HKCU, sUnInstPath, 'UninstallString', sUnInstallString);
  Result := sUnInstallString;
end;

function IsUpgrade: Boolean;
begin
  Result := (GetUninstallString() <> '');
end;

function InitializeSetup: Boolean;
var
  V: Integer;
  iResultCode: Integer;
  sUnInstallString: string;
  sUnInstPath: string;
begin
  Result := True; // in case when no previous version is found
  sUnInstPath := ExpandConstant('Software\Microsoft\Windows\CurrentVersion\Uninstall\{#emit SetupSetting("AppID")}_is1');
  if RegValueExists(HKLM, sUnInstPath, 'UninstallString') then  //Your App GUID/ID
  begin
    V := MsgBox(ExpandConstant('Hey! An old version of the TSM Application was detected. Do you want to uninstall it?'), mbInformation, MB_YESNO); //Custom Message if App installed
    if V = IDYES then
    begin
      sUnInstallString := GetUninstallString();
      sUnInstallString :=  RemoveQuotes(sUnInstallString);
      Exec(ExpandConstant(sUnInstallString), '', '', SW_SHOW, ewWaitUntilTerminated, iResultCode);
      Result := True; //if you want to proceed after uninstall
                //Exit; //if you want to quit after uninstall
    end
    else
      Result := False; //when older version present and not uninstalled
  end;
end;
"""


def find_files(dir, pattern):
    for root_path, _, file_names in os.walk(dir):
        for file_name in fnmatch.filter(file_names, pattern):
            yield os.path.join(root_path, file_name)


class Operations:
    @staticmethod
    def __dir__():
        return SUPPORTED_OPERATIONS


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
            os.makedirs(os.path.dirname(build_file_path), exist_ok=True)
            shutil.copy(path, build_file_path)

        # compile the resource files
        for path in find_files(RESOURCE_SRC_PATH, "*.qrc"):
            file_name = os.path.splitext(os.path.basename(path))[0]
            built_file_path = os.path.join(BUILD_DIR, "{}_rc.py".format(file_name))
            if os.system("pyrcc5 {} -o {}".format(path, built_file_path)) != 0:
                print("Failed to compile resource: {}".format(path))
                sys.exit(1)
            # compress the resource file
            module = import_module("build.{}_rc".format(file_name))
            with open(os.path.join(BUILD_DIR, "resources.data"), 'wb') as f:
                f.write(len(module.qt_resource_struct).to_bytes(4, byteorder="big"))
                f.write(len(module.qt_resource_name).to_bytes(4, byteorder="big"))
                f.write(len(module.qt_resource_data).to_bytes(4, byteorder="big"))
                f.write(module.qt_resource_struct)
                f.write(module.qt_resource_name)
                f.write(module.qt_resource_data)
            with open(built_file_path, 'w') as f:
                f.write(RESOURCE_CODE.format("resources.data"))

        # compile the UI files
        for path in find_files(UI_SRC_PATH, "*.ui"):
            built_file_path = os.path.join(BUILD_DIR, "{}_ui.py".format(os.path.splitext(os.path.basename(path))[0]))
            with open(built_file_path, 'w') as py_file:
                uic.compileUi(path, py_file)


    @staticmethod
    def run():
        os.system("{} {}".format(sys.executable, os.path.join(BUILD_DIR, MAIN_SCRIPT)))


    @staticmethod
    def dist_win():
        assert(sys.platform.startswith("win32"))
        from cx_Freeze import setup, Executable

        # Dependencies are automatically detected, but it might need fine tuning.
        build_exe_options = {
            'build_exe': UPDATER_DIST_DIR,
            'excludes': ["_ssl", "pydoc", "doctest", "test", "_hashlib", "_bz2", "_lzma", "zipfile", "gzip", "unicodedata", "logging"],
            'compressed': True
        }

        sys.argv = ["make.py", "build"]
        setup(
            name = UPDATER_NAME,
            version = "1.0", # this version is meaningless for our purposes, but required
            options = {'build_exe': build_exe_options},
            executables = [
                Executable(
                    UDPATER_MAIN_SCRIPT_PATH,
                    base = "Win32GUI",
                    targetName = UPDATER_NAME + ".exe",
                    targetDir = UPDATER_DIST_DIR
                )
            ]
        )

        # Dependencies are automatically detected, but it might need fine tuning.
        build_exe_options = {
            'build_exe': APP_DIST_DIR,
            'excludes': ["_ssl", "pydoc", "doctest", "test"],
            'compressed': True
        }

        sys.path.append("build/")
        sys.argv = ["make.py", "build"]
        setup(
            name = APP_NAME,
            version = "1.0", # this version is meaningless for our purposes, but required
            options = {'build_exe': build_exe_options},
            executables = [
                Executable(
                    os.path.join(BUILD_DIR, MAIN_SCRIPT),
                    base = "Win32GUI",
                    targetName = APP_NAME + ".exe",
                    targetDir = APP_DIST_DIR,
                    icon = os.path.join(RESOURCE_SRC_PATH, "logo.ico")
                )
            ]
        )

        # manually copy some dlls we've pre-built
        dll_prebuilt = ["icudt53.dll"]
        for dll in dll_prebuilt:
            src_path = os.path.join(RESOURCE_SRC_PATH, dll)
            dst_path = os.path.join(APP_DIST_DIR, dll)
            if os.path.isfile(src_path):
                print("Copy DLL {} to {}".format(src_path, dst_path))
                shutil.copy(src_path, dst_path)

        # manually copy resource binary files
        resource_files = ["resources.data"]
        for resource_file in resource_files:
            src_path = os.path.join(BUILD_DIR, resource_file)
            dst_path = os.path.join(APP_DIST_DIR, resource_file)
            if os.path.isfile(src_path):
                print("Copy resource data file {} to {}".format(src_path, dst_path))
                shutil.copy(src_path, dst_path)

        # generate the ISS file
        source_lines = []
        for root_path, _, files in os.walk(APP_DIST_DIR):
            root_path = os.path.relpath(root_path, APP_DIST_DIR).replace("\\", "/")
            for file_name in files:
                path = os.path.join(root_path, file_name).replace("/", "\\")
                if root_path == ".":
                    source_lines += ["Source: \"app\\{}\"; DestDir: \"{{app}}\\app\"".format(file_name)]
                else:
                    source_lines += ["Source: \"app\\{}\\{}\"; DestDir: \"{{app}}\\app\\{}\"".format(root_path, file_name, root_path)]
        for root_path, _, files in os.walk(UPDATER_DIST_DIR):
            root_path = os.path.relpath(root_path, UPDATER_DIST_DIR).replace("\\", "/")
            for file_name in files:
                path = os.path.join(root_path, file_name).replace("/", "\\")
                if root_path == ".":
                    source_lines += ["Source: \"updater\\{}\"; DestDir: \"{{app}}\\updater\"".format(file_name)]
                else:
                    source_lines += ["Source: \"updater\\{}\\{}\"; DestDir: \"{{app}}\\updater\\{}\"".format(root_path, file_name, root_path)]
        with open(os.path.join(BUILD_DIR, "inno.iss"), 'w') as f:
            f.write(INNO_SETUP_CODE % "\n".join(source_lines))

        # compile the ISS file
        os.system("{} /O{} {}".format(ISCC_PATH, BUILD_DIR, os.path.join(BUILD_DIR, "inno.iss")))


    @staticmethod
    def dist_mac():
        assert(sys.platform.startswith("darwin"))
        from cx_Freeze import setup, Executable

        # Dependencies are automatically detected, but it might need fine tuning.
        build_exe_options = {
            #'build_exe': UPDATER_DIST_DIR,
            'excludes': ["_ssl", "pydoc", "doctest", "test", "_hashlib", "_bz2", "_lzma", "zipfile", "gzip", "unicodedata", "logging"],
            'compressed': True
        }

        sys.argv = ["make.py", "build", "bdist_mac"]
        setup(
            name = UPDATER_NAME,
            version = "1.0", # this version is meaningless for our purposes, but required
            options = {'build_exe': build_exe_options, 'bdist_mac': {'bundle_name': UPDATER_NAME}},
            executables = [
                Executable(
                    UDPATER_MAIN_SCRIPT_PATH,
                    #targetName = UPDATER_NAME,
                    #targetDir = UPDATER_DIST_DIR
                )
            ]
        )

        # Dependencies are automatically detected, but it might need fine tuning.
        build_exe_options = {
            'build_exe': APP_DIST_DIR,
            'excludes': ["_ssl", "pydoc", "doctest", "test"],
            'compressed': True
        }

        sys.path.append("build/")
        sys.argv = ["make.py", "build", "bdist_mac"]
        setup(
            name = APP_NAME,
            version = "1.0", # this version is meaningless for our purposes, but required
            options = {'build_exe': build_exe_options, 'bdist_mac': {'bundle_name': APP_NAME}},
            executables = [
                Executable(
                    os.path.join(BUILD_DIR, MAIN_SCRIPT),
                    #targetName = APP_NAME + ".exe",
                    #targetDir = APP_DIST_DIR,
                    icon = os.path.join(RESOURCE_SRC_PATH, "logo.ico")
                )
            ]
        )

        # manually copy resource binary files
        resource_files = ["resources.data"]
        for resource_file in resource_files:
            src_path = os.path.join(BUILD_DIR, resource_file)
            dst_path = os.path.join(APP_DIST_DIR, resource_file)
            if os.path.isfile(src_path):
                print("Copy resource data file {} to {}".format(src_path, dst_path))
                shutil.copy(src_path, dst_path)


    # @staticmethod
    # def dist_mac():
        # assert(sys.platform.startswith("darwin"))
        # from setuptools import setup
        # sys.path.append("build/")

        # # setuptools uses argv, so we'll just fake it
        # sys.argv = ["make.py"]
        # import py2app
        # sys.argv.append("py2app")

        # setup(
            # name = APP_NAME,
            # app = [os.path.join(BUILD_DIR, MAIN_SCRIPT)],
            # options = {
                # 'py2app': {
                    # 'argv_emulation': True,
                    # 'iconfile': "resources/logo.icns",
                    # 'includes': ["sip"],
                    # 'dist_dir': APP_DIST_DIR,
                    # 'excludes': ["_ssl", 'pydoc', 'doctest', 'test'],
                    # 'compressed': True,
                # }
            # },
            # setup_requires = ['py2app'],
        # )


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
