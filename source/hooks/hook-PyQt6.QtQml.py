"""Keep the QML modules used by this widget and their native dependencies.

The generic Qt hook collects every installed QML plugin (including PDF and
3D engines). Filtering at analysis time also excludes their transitive DLLs.
"""
from pathlib import PurePath
from PyInstaller.utils.hooks.qt import add_qt6_dependencies, pyqt6_library_info

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
qml_binaries, qml_datas = pyqt6_library_info.collect_qtqml_files()
quick_modules = {'Controls', 'Templates', 'Shapes', 'Window', 'Layouts', 'NativeStyle'}


def used(entry):
    destination = PurePath(entry[1]).as_posix().split('/qml/', 1)[-1].split('/')
    return (destination[0] == 'QtQml' and (len(destination) == 1 or destination[1] in {'Models', 'WorkerScript'}) or
            destination[0] == 'QtQuick' and
            (len(destination) == 1 or destination[1] in quick_modules))


binaries += [entry for entry in qml_binaries if used(entry)]
datas += [entry for entry in qml_datas if used(entry)]
