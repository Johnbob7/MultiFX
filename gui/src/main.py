import sys
import time
from PyQt5.QtWidgets import QApplication
import modhostmanager
from qwidgets.core import MainWindow
import offboard
from input_adapter import PiInputAdapter, load_input_settings


def main():
    if offboard.try_load():
        print("Loaded data from USB drive!")
    app = QApplication(sys.argv)
    input_settings = load_input_settings()
    input_adapter = PiInputAdapter(input_settings)
    modhostmanager.startJackdServer()
    time.sleep(.5)
    main_window = MainWindow(input_adapter=input_adapter,
                             input_settings=input_settings)
    main_window.showFullScreen()
    input_adapter.start()
    exit_code = app.exec_()
    input_adapter.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
