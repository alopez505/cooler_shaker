# Liquid Sample Cooler-Shaker


## CSU Chico
### MECA/MECH 440 - Capstone Project
### Sponsor: SLAC National Accelerator Laboratory
![model](https://github.com/alopez505/cooler_shaker/blob/e59fdcb6c425a75c8efb639449e37c5c35bf737a/pics/model.jpg)
![GUI](https://github.com/alopez505/cooler_shaker/blob/e59fdcb6c425a75c8efb639449e37c5c35bf737a/pics/gui.PNG)

## Info
This code is used to control the **Liquid Sample Cooler-Shaker System** on a GUI using a Raspberry Pi in Python. This code also creates an asynchronous Modbus server. The system is adjustable via changes to the GUI or via writes to the Modbus server.

_**pySerial**_ is used to communicate with the temperature controller over a serial RS-485 connection.

_**Pymodbus**_ is used to connect to SLAC's Modbus TCP/IP. The package for _**Pymodbus**_ should be downloaded with _**Twisted**_ as well. 

_**Twisted**_ is an event driven networking engine that allows the Pi to be set up as a TCP/IP server.

_**PyQt5**_ is used to create the GUI and run various threads within the program.

_**PyQt5 Tools**_ gives additional tools to use with PyQt5.

_**PyQtGraph**_ is used to create the updating graph.

_**RPi.GPIO**_ is used to access the GPIO pins on the Raspberry Pi.

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

## Pictures
![P1](https://github.com/alopez505/cooler_shaker/blob/e59fdcb6c425a75c8efb639449e37c5c35bf737a/pics/p1.JPG)
![P2](https://github.com/alopez505/cooler_shaker/blob/e59fdcb6c425a75c8efb639449e37c5c35bf737a/pics/p2.JPG)
![complete](https://github.com/alopez505/cooler_shaker/blob/e59fdcb6c425a75c8efb639449e37c5c35bf737a/pics/complete.jpg)

If X server exits on boot its likely the USB-serial adapter for the TEC control board is not plugged in
