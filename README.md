# Liquid Sample Cooler-Shaker


### CSU Chico
### MECA/MECH 440 - Capstone Project
### Sponsor: SLAC National Accelerator Labratory
![imageofmachine](https://user-images.githubusercontent.com/31226424/110340390-0cd9ce00-7fde-11eb-8746-3745831877fd.jpg)

## Info
This code is used to control the system on a Raspberry Pi.

`temp_controller.py` was the inital code used to test and communicate with the RS-485 temperature controller.


Currently, development on `gui.py` is being done. It uses _**tkinter**_ to set up a GUI. The program controls the motor and communicates with the temperature controller.

Before adding the Modbus server to this code. Testing is being done on `pymodbus_updating_server.py`. This is so we can verify that a server can be successfully created before we start integrating the server into `gui.py`.

_**pySerial**_ is used to communictate with the temperature controller over a serial RS-485 connection.

_**Pymodbus**_ is used to connect to SLAC's Modbus TCP/IP. The package for pymodbus should be downloaded with _**Twisted**_ as well. _**Twisted**_ is an event driven networking engine that allows the Pi to be setup as a TCP/IP server.

## Packages
- [pySerial](https://pypi.org/project/pyserial/)
```bash
pip install pyserial
```
- [PyModbus](https://pymodbus.readthedocs.io/en/latest/index.html)
```bash
pip install -U pymodbus[twisted]
```
