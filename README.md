# Liquid Sample Cooler-Shaker


### CSU Chico
### MECA/MECH 440 - Capstone Project
### Sponsor: SLAC National Accelerator Laboratory
![imageofmachine](https://user-images.githubusercontent.com/31226424/110340390-0cd9ce00-7fde-11eb-8746-3745831877fd.jpg)

## Info
This code is used to control the **Liquid Sample Cooler-Shaker System** on a GUI using a Raspberry Pi in Python.

`temp_controller.py` was the initial code used to test and communicate with the RS-485 temperature controller.

`gui.py` was the initial GUI created to interact with the system. It uses _**tkinter**_ to set up a GUI. The program controls the motor and communicates with the temperature controller.

Before adding the Modbus server to `gui.py`. Testing was done on `pymodbus_updating_server.py`. This is for verification that a server can be successfully created before integration.

Development on `gui.py` using  _**tkinter**_ has since stopped. 

Development has moved to `pyqt5_cooler_shaker_modbus.py` using _**PyQt5**_. This is because _**PyQt5**_ has accessible threading capabilities for running the motor and the Modbus TCP/IP server in background threads. Also, the aesthetic to _**PyQt5**_ was preferred.

_**pySerial**_ is used to communicate with the temperature controller over a serial RS-485 connection.

_**Pymodbus**_ is used to connect to SLAC's Modbus TCP/IP. The package for _**Pymodbus**_ should be downloaded with _**Twisted**_ as well. 

_**Twisted**_ is an event driven networking engine that allows the Pi to be set up as a TCP/IP server.

_**PyQt5**_ is used to create the GUI and run various threads within the program.

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
