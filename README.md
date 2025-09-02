# MultiFX

MultiFX is an experimental multi-effects pedal project. This repository contains two main components:

- **Footswitch** – Arduino firmware that turns six digital inputs into MIDI note messages.
- **GUI** – A PyQt-based interface for managing plugins and communicating with the pedal.

## Getting Started

### Footswitch Firmware

The firmware lives in `Footswitch/Footswitch_Code/Footswitch_Code.ino`.
Open the file in the Arduino IDE and flash it to a board that exposes pins `D0`–`D5`
and a hardware serial port on `Serial1` for MIDI output. Each input toggles a MIDI note on its
own channel using interrupts; the `loop()` function is intentionally empty.

### GUI

The GUI resides under `GUI/` and requires Python 3 and PyQt5.
Install dependencies and run:

```bash
cd GUI
pip install pyqt5
python gui.py
```

## Repository Structure

```
Footswitch/        Arduino firmware and hardware files for the MIDI footswitch
GUI/               PyQt interface and related JSON/graphics assets
```

## Contributing

Pull requests and issue reports are welcome. This repository has been cleaned up to serve as a concise example; further improvements are encouraged.
