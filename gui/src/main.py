import sys
import time
from PyQt5.QtWidgets import QApplication
import modhostmanager
from plugin_manager import ensure_plugin_manifests
from qwidgets.core import MainWindow
import offboard
from utils import plugins_dir


def main():
    ensure_plugin_manifests(plugins_dir)
    if offboard.try_load():
        print("Loaded data from USB drive!")
    app = QApplication(sys.argv)
    modhostmanager.startJackdServer()
    time.sleep(.5)
    main_window = MainWindow()
    main_window.showFullScreen()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
