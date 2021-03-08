# Liquid Sample Cooler-Shaker


### CSU Chico
### MECA/MECH 440 - Capstone Project
### Sponsor: SLAC National Accelerator Labratory
![image](https://github.com/alopez505/cooler_shaker/issues/1#issue-824659455)

## Info
This code is used to control the system on a Raspberry Pi.

`test2.py` was the inital code used to test and communicate with the RS-485 temperature controller.


Currently, development on `temp_controller.py` is being done. It uses _**tkinter**_ to set up a GUI. The program controls the motor and communicates with the temperature controller.

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
