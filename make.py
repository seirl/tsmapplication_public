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
            'include_msvcr': True,
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
            'include_msvcr': True,
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

        # build the updater
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
                    targetName = UPDATER_NAME,
                    targetDir = UPDATER_DIST_DIR
                )
            ]
        )

        # build the app
        build_exe_options = {
            'excludes': ["_ssl", "pydoc", "doctest", "test"],
            'compressed': True
        }
        sys.path.append("build/")
        sys.argv = ["make.py", "build", "bdist_mac"]
        setup(
            name = APP_NAME,
            version = "1.0", # this version is meaningless for our purposes, but required
            options = {
                'build_exe': build_exe_options,
                'bdist_mac': {'bundle_name': APP_NAME, 'iconfile': os.path.join(RESOURCE_SRC_PATH, "logo.icns"),
                              'qt_menu_nib': "/usr/local/Cellar/qt5/5.5.1_2/plugins/platforms"},
                #'bdist_dmg': {'applications_shortcut': True, 'volume_label': "TSMApplication"}
            },
            executables = [
                Executable(
                    os.path.join(BUILD_DIR, MAIN_SCRIPT),
                    targetName = APP_NAME,
                    icon = os.path.join(RESOURCE_SRC_PATH, "logo.icns")
                )
            ]
        )

        # hack the .app to be structured like we want
        with open("build/TSMApplication.app/Contents/Info.plist") as f:
            lines = [x.replace("TSMApplication", "app/TSMApplication") for x in f]
        with open("build/TSMApplication.app/Contents/Info.plist", "w") as f:
            f.write("".join(lines))
        os.rename("build/TSMApplication.app/Contents/MacOS", "build/TSMApplication.app/Contents/app")
        os.mkdir("build/TSMApplication.app/Contents/MacOS")
        os.rename("build/TSMApplication.app/Contents/app", "build/TSMApplication.app/Contents/MacOS/app")
        os.rename("build/updater", "build/TSMApplication.app/Contents/MacOS/updater")
        os.system("install_name_tool -change /Library/Frameworks/Python.framework/Versions/3.4/Python " +
                  "@executable_path/Python build/TSMApplication.app/Contents/MacOS/updater/TSMUpdater")

        import subprocess
        platform_path = "build/TSMApplication.app/Contents/MacOS/app/platforms"
        platform_libs = os.listdir(platform_path)
        app_path = "build/TSMApplication.app/Contents/MacOS/app"
        paths = [
            "build/TSMApplication.app/Contents/MacOS/app",
            "build/TSMApplication.app/Contents/MacOS/app/platforms",
            "build/TSMApplication.app/Contents/MacOS/updater",
        ]
        for path in paths:
            for file_name in [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]:
                file_path = os.path.join(path, file_name)
                p = subprocess.Popen(["otool", "-L", file_path], stdout=subprocess.PIPE)
                references = p.stdout.readlines()[1:]
                for reference in references:
                    reference = reference.decode().strip().split()[0]
                    if reference.startswith("@rpath"):
                        lib = reference.split('/')[-1]
                        if lib in platform_libs:
                            new_path = "@executable_path/platforms/" + reference.split('/')[-1]
                        else:
                            new_path = "@executable_path/" + reference.split('/')[-1]
                        os.system("install_name_tool -change {} {} {}".format(reference, new_path, file_path))
        Operations.buildDMG()


    @staticmethod
    def buildDMG():
        dmgName = "TSMApplication.dmg"
        # Remove DMG if it already exists
        if os.path.exists(dmgName):
            os.unlink(dmgName)

        createargs = [
            'hdiutil', 'create', '-fs', 'HFSX', '-format', 'UDZO',
            "build/"+dmgName, '-imagekey', 'zlib-level=9', '-srcfolder',
            "build/TSMApplication.app", '-volname', "TSMApplication"
        ]

        if True:
            scriptargs = [
                'osascript', '-e', 'tell application "Finder" to make alias \
                file to POSIX file "/Applications" at POSIX file "%s"' %
                os.path.realpath("build")
            ]

            if os.spawnvp(os.P_WAIT, 'osascript', scriptargs) != 0:
                raise OSError('creation of Applications shortcut failed')

            createargs.append('-srcfolder')
            createargs.append("build" + '/Applications')

        # Create the dmg
        if os.spawnvp(os.P_WAIT, 'hdiutil', createargs) != 0:
            raise OSError('creation of the dmg failed')


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
