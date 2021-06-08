# Liquid Sample Cooler-Shaker


## CSU Chico
### MECA/MECH 440 - Capstone Project
### Sponsor: SLAC National Accelerator Laboratory
![imageofmachine](https://user-images.githubusercontent.com/31226424/110340390-0cd9ce00-7fde-11eb-8746-3745831877fd.jpg)

## Info
This code is used to control the **Liquid Sample Cooler-Shaker System** on a GUI using a Raspberry Pi in Python. This code also creates an asynchronous Modbus server. The program is adjustable via changes to the GUI or via writes to the Modbus server.

_**pySerial**_ is used to communicate with the temperature controller over a serial RS-485 connection.

_**Pymodbus**_ is used to connect to SLAC's Modbus TCP/IP. The package for _**Pymodbus**_ should be downloaded with _**Twisted**_ as well. 

_**Twisted**_ is an event driven networking engine that allows the Pi to be set up as a TCP/IP server.

_**PyQt5**_ is used to create the GUI and run various threads within the program.

**PyQt5 Tools**_ gives additional tools to use with PyQt5.

**PyQtGraph**_ is used to create the updating graph.

**RPi.GPIO**_ is used to access the GPIO pins on the Raspberry Pi.

## Packages
- [pySerial](https://pypi.org/project/pyserial/)
```bash
pip install pyserial
```

- [PyModbus](https://pymodbus.readthedocs.io/en/latest/index.html)
```bash
pip install -U pymodbus[twisted]
```

- [PyQt5](https://pypi.org/project/PyQt5/)
```bash
pip install PyQt5
```

- [PyQt5 Tools](https://pypi.org/project/pyqt5-tools/)
```bash
pip install pyqt5-tools
```

- [PyQtGraph](https://pypi.org/project/pyqtgraph/)
```bash
pip install pyqtgraph
```

- [RPi.GPIO](https://pypi.org/project/RPi.GPIO/)
```bash
pip install RPi.GPIO
```
