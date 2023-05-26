# --------------------------------
# Written by: Alexander Lopez
# Github: https://github.com/alopez505/cooler_shaker
# --------------------------------
#
# --------------------------------
# This program is meant to be used with the Cooler-Shaker System
# Hardware:
# - Raspberry Pi 3
# - Touchscreen of 800 x 480
# - TE Tech TC-36-25-RS485 Temperature Controller
# - TE Tech AC-046 Peltier Module
# - STEP / DIR stepper motor driver
# - 200 count stepper motor
# - USB to RS-485 converter
# - Power Supply
# --------------------------------
#
# --------------------------------
# PyQt5 is the main framework used to create the GUI
#
# Each window used in this program inherits QMainWindow
#
# QThread is used to take advantage of multithreading. The GUI controlls the main thread, 
# therfore the Modbus server and motor worker must run in seperate threads
# --------------------------------
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QTimer, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow

# --------------------------------
# PyQtGraph creates the graph on the mainscreen
# note: Although graph can be turned of in "General Setting" menu, the graph is still running
# --------------------------------
from pyqtgraph import PlotWidget, mkPen

# --------------------------------
# PyModbus creates Modbus server
# This code uses an asynchronous server
# --------------------------------
from pymodbus3.version import version
from pymodbus3.server.asynchronous import StartTcpServer
from pymodbus3.device import ModbusDeviceIdentification
from pymodbus3.datastore import ModbusSequentialDataBlock
from pymodbus3.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus3.transaction import ModbusRtuFramer, ModbusAsciiFramer

# --------------------------------
# twisted is used for the LoopingCall functionality
# LoopingCall alows a function to be called repeatedly
# --------------------------------
from twisted.internet.task import LoopingCall

# --------------------------------
# time for all time based events
# --------------------------------
import time
from time import sleep

# --------------------------------
# sys used to configure with Python runtime environment
# --------------------------------
import sys

# --------------------------------
# serial module alows for communication with the "TE Tech TC-36-25-RS485" temperature controller
# --------------------------------
import serial
ser=serial.Serial('/dev/ttyUSB0', 115200, timeout=1)       # using /dev/ttyUSB0 port on Raspi 

# --------------------------------
# logging module to keep track of changes in the system
# --------------------------------
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

# --------------------------------
# RPi.GPIO module allows access to GPIO pins on Raspi
# Pins are connected to a "STEP & DIR" motor driver
# --------------------------------

import RPi.GPIO as GPIO         #RPIO module to use Raspi GPIO pins
DIR = 20                        # pin 20
STEP = 21                       # pin 21
CW = 1                          # CW = 1, CCW = 0 for STEP & DIR controller
CCW = 0                         
# -- Setup --
GPIO.setmode(GPIO.BCM)          
GPIO.setup(DIR, GPIO.OUT)       
GPIO.setup(STEP, GPIO.OUT)      


# --------------------------------
# Using a NEMA 23 stepper with 200 steps per rev
# --------------------------------
motorSteps = 200 * 16

# --------------------------------
# Checksum function to send the correct values to controller
# More information in: TE Tech TC-36-25 RS485 Manual
# --------------------------------
def calc_checksum(AA1,AA2,CC1,CC2,DD1,DD2,DD3,DD4,DD5,DD6,DD7,DD8):
    command_string = [AA1,AA2,CC1,CC2,DD1,DD2,DD3,DD4,DD5,DD6,DD7,DD8]
    val=0
    for x in range (0,12):
        val += ord(command_string[x])
    val_hex=hex(val)
    SS1=val_hex[-2]
    SS2=val_hex[-1]
    return SS1, SS2

# --------------------------------
# "ServerWorker" creates the Modbus server in seperate thread via QThread
#
# Holding registers and input registers are saved as float variables in IEEE 745 format
# 32 bits are needed to save each float value in IEEE 745 format
# Holding registers and input registers only allow for 16 bits
# Therefore 2 addresses will hold each variable,
# ex: Set Temperature stored in holding register at address [0] and [1] 
# (16 bits at [0], 16 bits at [1])
#  
# -------- VARIABLES IN MODBUS SERVER --------
#
# COILS 
# +---------+--------------+------+------------------------------------+--------------+
# | Address | Name         | Type | Interpretation                     | Read / Write |
# +---------+--------------+------+------------------------------------+--------------+
# | 0       | Motor Status | BOOL | False = Motor off, True = Motor on | Read & Write |
# +---------+--------------+------+------------------------------------+--------------+
#
# DISCRETE INPUTS
# +---------+---------------------------+------+------------------+--------------+
# | Address | Name                      | Type | Interpretation   | Read / Write |
# +---------+---------------------------+------+------------------+--------------+
# | 0       | Alarm - Low Input Voltage | BOOL | False = No alarm | Read         |
# +---------+---------------------------+------+------------------+--------------+
# | 1       | Alarm - Thermistor Error  | BOOL | False = No alarm | Read         |
# +---------+---------------------------+------+------------------+--------------+
# | 2       | Alarm - Over Current      | BOOL | False = No alarm | Read         |
# +---------+---------------------------+------+------------------+--------------+
# | 3       | Alarm - Low Temp Warning  | BOOL | False = No alarm | Read         |
# +---------+---------------------------+------+------------------+--------------+
# | 4       | Alarm - High Temp Warning | BOOL | False = No alarm | Read         |
# +---------+---------------------------+------+------------------+--------------+
#
# HOLDING REGISTERS
# +---------+-------------------------------+------------------+----------------------------------------------------------+--------------+
# | Address | Name                          | Type             | Description                                              | Read / Write |
# +---------+-------------------------------+------------------+----------------------------------------------------------+--------------+
# | 0       | Set Temperature               | Float - IEEE 745 | Set Temperature to reach (C)                             | Read & Write |
# +---------+-------------------------------+------------------+----------------------------------------------------------+--------------+
# | 1       | Set Temperature (2)           |                  |                                                          |              |
# +---------+-------------------------------+------------------+----------------------------------------------------------+--------------+
# | 2       | Motor Speed                   | Float - IEEE 745 | Speed of motor (degrees/s)                               | Read & Write |
# +---------+-------------------------------+------------------+----------------------------------------------------------+--------------+
# | 3       | Motor Speed (2)               |                  |                                                          |              |
# +---------+-------------------------------+------------------+----------------------------------------------------------+--------------+
# | 4       | Motor Degrees of Rotation     | Float - IEEE 745 | Degrees of movement provided by motor (degrees)          | Read & Write |
# +---------+-------------------------------+------------------+----------------------------------------------------------+--------------+
# | 5       | Motor Degrees of Rotation (2) |                  |                                                          |              |
# +---------+-------------------------------+------------------+----------------------------------------------------------+--------------+
# | 6       | Motor Dwell Time              | Float - IEEE 745 | Time between clockwise and counterclockwise rotation (s) | Read & Write |
# +---------+-------------------------------+------------------+----------------------------------------------------------+--------------+
# | 7       | Motor Dwell Time (2)          |                  |                                                          |              |
# +---------+-------------------------------+------------------+----------------------------------------------------------+--------------+
#
# INPUT REGISTERS
# +---------+-------------------------+------------------+-------------------------------------------------+--------------+
# | Address | Name                    | Type             | Description                                     | Read / Write |
# +---------+-------------------------+------------------+-------------------------------------------------+--------------+
# | 0       | Current Temperature     | Float - IEEE 745 | Current temperature reading from thermistor (C) | Read         |
# +---------+-------------------------+------------------+-------------------------------------------------+--------------+
# | 1       | Current Temperature (2) |                  |                                                 |              |
# +---------+-------------------------+------------------+-------------------------------------------------+--------------+
#
# --------------------------------
class ServerWorker(QThread):

    # Signals used to send data between ServerWorker and main thread
    updateModbusValues = pyqtSignal()
    updateGUIValues = pyqtSignal()
    updateCurrentTemp = pyqtSignal()
    SendSetTemp = pyqtSignal()
    setSetTemp = pyqtSignal()
    sendAlarmStatus = pyqtSignal()
    motorStatus = pyqtSignal()

    def __init__(self):
        super(ServerWorker, self).__init__()

        # Variables inside Modbus server
        # "MB" specifies that these are variables in "ModBus Server"
        self.MB_set_temp = 0.0
        self.MB_current_temp = 0.0
        self.MB_motor_speed = 0.0
        self.MB_motor_dor = 0.0
        self.MB_motor_dwell = 0.0

        # --- FLAGS ---

        # flags to determine if motor is running
        self.MB_motor_on = False
        self.GUI_motorFlag = False
        # Alarm flags stored as discrete inputs
        self.MB_alarm_low_voltage = False
        self.MB_alarm_therm = False
        self.MB_alarm_overcurrent = False
        self.MB_alarm_lowtemp = False
        self.MB_alarm_hightemp = False

    # ----------------
    # "work" is called once
    #
    # At the end of "work", LoopingCall is used from twisted module
    # This begins the updating writer function to be called repeatedly after a specified amount of time
    #
    # The function "ModbusSlaveContext" creates the variables in the Modbus Server
    #
    #   co = coils
    #   di = discrete inputs
    #   hr = holding registers
    #   ir = input registers
    #
    # ex:   hr=ModbusSequentialDataBlock(0, [0]*8),   
    # The line above creates 8 Holding Registers starting at address 0 (Address 0 for holding registers) with values of 0
    # ----------------
    def work(self):
        log.debug("Creating Modbus server in seperate thread via QThread")
        log.info(self.currentThread())
        sleep(0.1)
        store = ModbusSlaveContext(
            co=ModbusSequentialDataBlock(0, [0]*1),
            di=ModbusSequentialDataBlock(0, [0]*5),
            hr=ModbusSequentialDataBlock(0, [0]*8),
            ir=ModbusSequentialDataBlock(0, [0]*2),zero_mode=True)      # zero_mode is true, so variables are stored starting at address 0, not 1
        context = ModbusServerContext(slaves=store, single=True)
        # ----------------------------------------------------------------------- # 
        # initialize the server information
        # ----------------------------------------------------------------------- # 
        # default server info
        identity = ModbusDeviceIdentification()
        identity.VendorName = 'pymodbus'
        identity.ProductCode = 'PM'
        identity.VendorUrl = 'http://github.com/riptideio/pymodbus/'
        identity.ProductName = 'pymodbus Server'
        identity.ModelName = 'pymodbus Server'
        identity.MajorMinorRevision = version.short()
        time = 5  # 5 second delay for LoopingCall
        loop = LoopingCall(f=self.updating_writer, a=(context,))
        loop.start(time, now=False) 
        sleep(0.1)  # initially delay by time
        self.initSetTemp=self.readSetTemp()     # read set temp value saved on temperature controller
        log.info("Set Temperature initialized from saved data on temerature controller: " + str(self.initSetTemp))
        self.setSetTemp.emit()      # send set temperature value saved on temperature controller to GUI
        initSetTemp_ieee1, initSetTemp_ieee2 = self.float_to_ieee(self.initSetTemp)
        context[0x00].setValues(3, 0x00, [initSetTemp_ieee1, initSetTemp_ieee2, 17076, 0, 17332, 0, 16128, 0])
        self.MB_set_temp=self.initSetTemp
        StartTcpServer(context, identity=identity, address=("Localhost",5020))

    
    # ----------------
    # "updating_writer" function is called repeatedly via "LoopingCall"
    # 
    # This function performs all the tasks that need to be done continously such as:
    #       - Run asynchronous Modbus server
    #       - Check variables from main screen GUI and compare to  variables in ModBus Server
    #           -- Determine if changes were made via GUI changes or via Modbus writes
    #       - Read current temperature
    #       - Converts data
    #       - Check for alarms
    #
    #  Broken into sections for looking at changes in HR, IR, DI, and CO 
    # ----------------
    def updating_writer(self, a):
        """ A worker process that runs every so often and
        updates live values of the context. It should be noted
        that there is a race condition for the update.

        :param arguments: The input arguments to the call
        """
        log.debug("Updating the context")
        HR_values_old = [self.MB_set_temp, self.MB_motor_speed, self.MB_motor_dor, self.MB_motor_dwell]
        log.info("Last Holding Register values in server: " + str(HR_values_old))
        self.updateModbusValues.emit()      # signal that changes MB variables to ones in GUI
        sleep(0.1)
        HR_values_gui = [self.MB_set_temp, self.MB_motor_speed, self.MB_motor_dor, self.MB_motor_dwell]
        log.info("Holding Register values in GUI: " + str(HR_values_gui))
        context = a[0]
        register_hr = 3        # 1=co , 2=di, 3=hr, 4=ir
        register_ir = 4
        register_di = 2
        register_co = 1
        slave_id = 0x00
        address = 0x00      #starting address for values
        # Convert each float variable to 2 seperate 16-bit values (HR's & IR's)
        # Each variable set to ieee1 and ieee2
        # ---- HOLDING REGISTER SECTION ----
        set_temp_ieee1, set_temp_ieee2 = self.float_to_ieee(self.MB_set_temp)
        motor_speed_ieee1, motor_speed_ieee2 = self.float_to_ieee(self.MB_motor_speed)
        motor_dor_ieee1, motor_dor_ieee2 = self.float_to_ieee(self.MB_motor_dor)
        motor_dwell_ieee1, motor_dwell_ieee2 = self.float_to_ieee(self.MB_motor_dwell)
        hr_values_ieee = [set_temp_ieee1, set_temp_ieee2, motor_speed_ieee1, motor_speed_ieee2, motor_dor_ieee1, motor_dor_ieee2, motor_dwell_ieee1, motor_dwell_ieee2]
        hr_values_inServer_ieee = context[slave_id].getValues(register_hr, address, count=8)
        log.info("Holding Register Values in GUI in IEEE format: " + str(hr_values_ieee))
        log.info("Current Register Values in server in IEEE format: "+ str(hr_values_inServer_ieee))
        # Compare variables to deterime if any changes
        if HR_values_old != HR_values_gui:                    
            # GUI Values Changed - Sets Modbus values to values set in GUI                  
            log.debug("Last Holding Register Values do not match ones in GUI, changing to values set in GUI")
            context[slave_id].setValues(register_hr, address, hr_values_ieee)
            log.debug("Set Holding Values to: " + str(HR_values_gui))
        elif hr_values_inServer_ieee != hr_values_ieee:
            # Server Values Changed - Sets GUI values to values set in server
            log.debug("Holding Register Values IEEE do not match Holding Register values in GUI IEEE, changing to values set in server")
            st=round(self.ieee745_to_float(bin(hr_values_inServer_ieee[0]).replace('0b','').zfill(16)+bin(hr_values_inServer_ieee[1]).replace('0b','').zfill(16)),2)
            ms=round(self.ieee745_to_float(bin(hr_values_inServer_ieee[2]).replace('0b','').zfill(16)+bin(hr_values_inServer_ieee[3]).replace('0b','').zfill(16)),1)
            mdor=round(self.ieee745_to_float(bin(hr_values_inServer_ieee[4]).replace('0b','').zfill(16)+bin(hr_values_inServer_ieee[5]).replace('0b','').zfill(16)),1)
            md=round(self.ieee745_to_float(bin(hr_values_inServer_ieee[6]).replace('0b','').zfill(16)+bin(hr_values_inServer_ieee[7]).replace('0b','').zfill(16)),1)
            if st != self.MB_set_temp:
                # Send "set temp" to temp controller if write to modbus server
                self.MB_set_temp = st
                self.SendSetTemp.emit()
            self.MB_set_temp = st
            self.MB_motor_speed = ms
            self.MB_motor_dor = mdor
            self.MB_motor_dwell = md
            sleep(0.1)
            self.updateGUIValues.emit()
            log.debug("Updated GUI with Modbus Inputs")
        else:
            pass
        # ---- INPUT REGISTER SECTION ----
        current_temp = round(self.read_current_temp(),2)
        self.MB_current_temp = current_temp
        log.info("Current temperature: " + str(current_temp))
        log.debug("Writing Current temperature to Input Register")
        current_temp_ieee1, current_temp_ieee2 = self.float_to_ieee(current_temp)
        ir_values_ieee = [current_temp_ieee1, current_temp_ieee2]
        log.info("New Input Register Values in IEEE : " + str(ir_values_ieee))
        context[slave_id].setValues(register_ir, address, ir_values_ieee)
        self.updateCurrentTemp.emit()
        # ---- DISCRETE INPUTS SECTION ----
        self.alarm_lst=self.checkAlarms()
        self.sendAlarmStatus.emit()
        co_values_inserver = context[slave_id].getValues(register_co, address, count=1)
        sleep(0.1)
        di_values = [self.MB_alarm_low_voltage, self.MB_alarm_therm, self.MB_alarm_overcurrent, self.MB_alarm_lowtemp, self.MB_alarm_hightemp]
        context[slave_id].setValues(register_di, address, di_values)
        self.GUI_motorFlag = False
        # ---- COILS SECTION ----
        if (co_values_inserver[0] != self.MB_motor_on) and (self.GUI_motorFlag == False):
            log.debug("Coils changed from Modbus, setting motor to off/on determined from Modbus")
            self.motorStatus.emit()
        else:
            co_values = [self.MB_motor_on]
            context[slave_id].setValues(register_co, address, co_values)

    # ----------------
    # "float_to_ieee" function is used to convert the float values in Python into 2 16-bit values that represent a 32-bit IEEE 745 float value
    # 
    # Parameter:    n - Floating point value
    #
    # Return:       fin1 - First 16-bits of float value "n", in IEEE 745 format (bits 0-15)
    #               fin2 - Last 16-bits of float value "n", in IEEE 745 format (bits 16-31)
    # ----------------
    def float_to_ieee(self,n):
        sign = '0'            # 0=positive, 1=negative
        if n < 0:
            sign = '1'
            n = n * -1
        elif n==0.0:
            return 0, 0
        whole_num, dec_num = str(n).split('.')
        dec = str(bin(int(whole_num)))[2:]+'.'
        for x in range(30):
            dec_num = str('0.')+dec_num
            temp = str(float(dec_num)*2)
            whole_num, dec_num = temp.split('.')
            dec+=whole_num
        dotPlace = dec.find('.')
        onePlace = dec.find('1')
        dec = dec.replace(".","")
        dotPlace -= 1
        if onePlace > dotPlace:     # n < 1
            onePlace -= 1
        mantissa = dec[onePlace+1:]
        mantissa = mantissa[0:23]
        exp = dotPlace - onePlace
        exp_bits = exp + 127
        exp_bits = bin(exp_bits)[2:].zfill(8)
        ieee_num = sign + exp_bits + mantissa
        fin1, fin2 = ieee_num[0:16], ieee_num[16:32]
        fin1, fin2 = int(fin1,2), int(fin2,2)
        return fin1, fin2

    # ----------------
    # "ieee745_to_float" function is used to convert 32-bit binary IEEE 745 values to floating point values
    # 
    # Parameter:    N - binary 32-bit IEEE 745 floating point value
    #
    # Return:       x - Value of "N" in floating point format (decimal)
    # ----------------
    def ieee745_to_float(self,N): # ieee-745 bits (max 32 bit)
        if N =='00000000000000000000000000000000':
            return 0.0
        a = int(N[0])        # sign,     1 bit
        b = int(N[1:9],2)    # exponent, 8 bits
        c = int("1"+N[9:], 2)# fraction, len(N)-9 bits
        x = (-1)**a * c /( 1<<( len(N)-9 - (b-127) ))
        return x

    # ----------------
    # "read_current_temp" function polls the temperature controller to read the temperature of the thermistor
    #
    # Parameter:    n/a
    #
    # Return:       crnt_temp - Temperature detected by thermistor
    # ----------------
    def read_current_temp(self):
        buf=['*','0','0','0','0','0','0','0','0','0','0','^']
        A1,A2 = '0','2'
        C1,C2 = '0','1'
        D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','0'
        S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
        bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
        for pn in range(0,16):
            ser.write(bst[pn].encode())
        for pn in range(0,12):
            buf[pn]=ser.read(1)
        crnt_temp  = self.hexc2dec(buf) / 100
        return crnt_temp

    # ----------------
    # "readSetTemp" function polls to temperature controller to read the set temperature
    # 
    # Parameter:    n/a
    #
    # Return:       x - Value of "N"
    # ----------------
    def readSetTemp(self):
        buf=['*','0','0','0','0','0','0','0','0','0','0','^']
        A1,A2 = '0','2'
        C1,C2 = '5','0'
        D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','0'
        S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
        bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
        for pn in range(0,16):
            ser.write(bst[pn].encode())
        for pn in range(0,12):
            buf[pn]=ser.read(1)
        read_set_temp=self.hexc2dec(buf)/100
        return read_set_temp

    # ----------------
    # "checkAlarms" function polls to temperature controller to detect if any alarms have been triggered
    # 
    # Parameter:    n/a
    #
    # Return:       alarm_list - List of binary values with size of 7. Each binary value represents a different alarm
    # ----------------
    def checkAlarms(self):
        buf=['*','0','0','0','0','0','0','0','0','0','0','^']
        A1,A2 = '0','2'
        C1,C2='0','5'
        D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','0'
        S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
        bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
        for pn in range(0,16):
            ser.write(bst[pn].encode())
        for pn in range(0,12):
            buf[pn]=ser.read(1)
        alarm_int=int(self.hexc2dec(buf))
        alarm_list=[int(i) for i in bin(alarm_int)[2:]]
        while len(alarm_list) < 7:
            alarm_list.insert(0,0)
        return alarm_list

    # ----------------
    # "hex2dec" function converts data in the form of hex values in string format to decimal values
    # Used when reading the TE Tech TC-36-25-RS485 temperature controller
    # Takes the hex values saved as char values in positions 1-9 of the list. 
    # Positions [1-9] contain the data meant to be converted
    # See TC-36-25-RS485 Manual for more info
    #
    # Parameter:    bufp - List of hex values saved as individual char values within a list. Data is stored in bufp[1:9]
    #
    # Return:       newval - Data from bufp converted to decimal
    # ----------------
    def hexc2dec(self,bufp):
        newval=0
        divvy=pow(16,7)
        #sets the word size to DDDDDDDD
        for pn in range (1,9):
            vally=ord(bufp[pn])
            if(vally < 97):
                subby=48
            else:
                subby=87
                    # ord() converts the character to the ascii number value
            newval+=((ord(bufp[pn])-subby)*divvy)
            divvy/=16
            if(newval > pow(16,8)/2-1):
                newval=newval-pow(16,8)
                   #distinguishes between positive and negative numbers
        return newval


# --------------------------------
# MotorWorker performs motor operations in a seperate thread via QThread
# Used in Start/Stop button toggle and with rotate fwd and rotate rev buttons
# --------------------------------
class MotorWorker(QThread):
    finished = pyqtSignal()  # our signal out to the main thread to alert it we've completed our work

    def __init__(self):
        super(MotorWorker, self).__init__()
        self.working = True  # this is our flag to control our loop
        self.fwd_working = True
        self.rev_working = True
        self.speed = 0.0
        self.dor = 0.0
        self.dwell = 0.0

    # work called when Start/Stop Button is toggled
    def work(self):
        log.debug("Motor Running")
        sec_per_step = 0.1/self.speed
        while self.working:
            time.sleep(self.dwell)
            #print("sec perstep: ", sec_per_step)
            GPIO.output(DIR,CW)
            i = 0
            for x in range(round(self.dor/360*motorSteps)):
                print ('CW'+str(i))
                GPIO.output(STEP,GPIO.HIGH)
                time.sleep(sec_per_step)
                GPIO.output(STEP,GPIO.LOW)
                time.sleep(sec_per_step)
            time.sleep(self.dwell)
            GPIO.output(DIR,CCW)
            i = 0
            for x in range(round(self.dor/360*motorSteps)):
                print ('CCW'+str(i))
                GPIO.output(STEP,GPIO.HIGH)
                time.sleep(sec_per_step)
                GPIO.output(STEP,GPIO.LOW)
                time.sleep(sec_per_step)
                i +=1
        log.debug("Ended Motor Operation")
        self.finished.emit() # alert our gui that the loop stopped


    def work_fwd(self):
        GPIO.output(DIR,CW)
        while self.fwd_working:
            GPIO.output(STEP,GPIO.HIGH)
            time.sleep(0.001)
            GPIO.output(STEP,GPIO.LOW)
            time.sleep(0.001)
            log.debug("Rotate Forward Toggle")
        self.finished.emit() # alert our gui that the loop stopped

    def work_rev(self):
        GPIO.output(DIR,CCW)
        while self.rev_working:
            GPIO.output(STEP,GPIO.HIGH)
            time.sleep(0.001)
            GPIO.output(STEP,GPIO.LOW)
            time.sleep(0.001)
            log.debug("Rotate Reverse Toggle")
        self.finished.emit() # alert our gui that the loop stopped

# --------------------------------
# MotorWindow creates the Motor Settings window
# --------------------------------
class MotorWindow(QMainWindow):

    saveMotorSettings = pyqtSignal()    # Signal used to save settings upon "Save Settings and Close"

    def __init__(self):
        super(MotorWindow, self).__init__()
        self.setGeometry(0, 0, 800, 480)
        self.initUI()

    def initUI(self):
        self.setObjectName("Motor Window")
        self.resize(800, 480)
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.PlaceholderText, brush)
        self.setPalette(palette)
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.setTabShape(QtWidgets.QTabWidget.Rounded)
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")

        self.deg_sec_label = QtWidgets.QLabel(self.centralwidget)
        self.deg_sec_label.setGeometry(QtCore.QRect(660, 30, 81, 31))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(14)
        self.deg_sec_label.setFont(font)
        self.deg_sec_label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.deg_sec_label.setObjectName("deg_sec_label")

        self.Motor_dwell_label = QtWidgets.QLabel(self.centralwidget)
        self.Motor_dwell_label.setGeometry(QtCore.QRect(330, 130, 211, 41))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(24)
        self.Motor_dwell_label.setFont(font)
        self.Motor_dwell_label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.Motor_dwell_label.setObjectName("Motor_dwell_label")

        self.msSpinBox = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.msSpinBox.setGeometry(QtCore.QRect(540, 10, 111, 51))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.PlaceholderText, brush)
        self.msSpinBox.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(38)
        font.setBold(True)
        font.setWeight(75)
        self.msSpinBox.setFont(font)
        self.msSpinBox.setInputMethodHints(QtCore.Qt.ImhFormattedNumbersOnly)
        self.msSpinBox.setFrame(False)
        self.msSpinBox.setAlignment(QtCore.Qt.AlignCenter)
        self.msSpinBox.setReadOnly(False)
        self.msSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.msSpinBox.setDecimals(0)
        self.msSpinBox.setMaximum(360.0)
        self.msSpinBox.setSingleStep(15.0)
        self.msSpinBox.setProperty("value", 90.0)
        self.msSpinBox.setObjectName("msSpinBox")

        self.dwellSpinBox = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.dwellSpinBox.setGeometry(QtCore.QRect(540, 110, 111, 61))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.PlaceholderText, brush)
        self.dwellSpinBox.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(34)
        font.setBold(True)
        font.setWeight(75)
        self.dwellSpinBox.setFont(font)
        self.dwellSpinBox.setInputMethodHints(QtCore.Qt.ImhFormattedNumbersOnly)
        self.dwellSpinBox.setFrame(False)
        self.dwellSpinBox.setAlignment(QtCore.Qt.AlignCenter)
        self.dwellSpinBox.setReadOnly(False)
        self.dwellSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.dwellSpinBox.setDecimals(1)
        self.dwellSpinBox.setMaximum(10.0)
        self.dwellSpinBox.setSingleStep(0.5)
        self.dwellSpinBox.setProperty("value", 0.5)
        self.dwellSpinBox.setObjectName("dwellSpinBox")

        self.graphicsView_motor = QtWidgets.QGraphicsView(self.centralwidget)
        self.graphicsView_motor.setGeometry(QtCore.QRect(0, 0, 261, 181))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        self.graphicsView_motor.setPalette(palette)
        self.graphicsView_motor.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.graphicsView_motor.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.graphicsView_motor.setObjectName("graphicsView_motor")

        self.line_vert_motor = QtWidgets.QFrame(self.centralwidget)
        self.line_vert_motor.setGeometry(QtCore.QRect(250, 0, 20, 181))
        self.line_vert_motor.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_vert_motor.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_vert_motor.setObjectName("line_vert_motor")

        self.Motor_speed_label = QtWidgets.QLabel(self.centralwidget)
        self.Motor_speed_label.setGeometry(QtCore.QRect(410, 20, 131, 41))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(24)
        self.Motor_speed_label.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(24)
        self.Motor_speed_label.setFont(font)
        self.Motor_speed_label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.Motor_speed_label.setObjectName("Motor_speed_label")

        self.SaveAndCloseMotor = QtWidgets.QPushButton(self.centralwidget)
        self.SaveAndCloseMotor.setGeometry(QtCore.QRect(20, 20, 221, 141))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(13)
        self.SaveAndCloseMotor.setFont(font)
        self.SaveAndCloseMotor.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.SaveAndCloseMotor.setObjectName("SaveAndCloseMotor")

        self.dwell_sec_label = QtWidgets.QLabel(self.centralwidget)
        self.dwell_sec_label.setGeometry(QtCore.QRect(660, 140, 51, 31))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(14)
        self.dwell_sec_label.setFont(font)
        self.dwell_sec_label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.dwell_sec_label.setObjectName("dwell_sec_label")

        self.SpeedLabel = QtWidgets.QLabel(self.centralwidget)
        self.SpeedLabel.setGeometry(QtCore.QRect(10, 190, 251, 41))
        font = QtGui.QFont()
        font.setPointSize(16)
        self.SpeedLabel.setFont(font)
        self.SpeedLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.SpeedLabel.setObjectName("SpeedLabel")

        self.MinusSpeed = QtWidgets.QPushButton(self.centralwidget)
        self.MinusSpeed.setGeometry(QtCore.QRect(10, 360, 250, 111))
        font = QtGui.QFont()
        font.setPointSize(48)
        self.MinusSpeed.setFont(font)
        self.MinusSpeed.setObjectName("MinusSpeed")

        self.DORLabel = QtWidgets.QLabel(self.centralwidget)
        self.DORLabel.setGeometry(QtCore.QRect(270, 190, 251, 41))
        font = QtGui.QFont()
        font.setPointSize(13)
        self.DORLabel.setFont(font)
        self.DORLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.DORLabel.setObjectName("DORLabel")

        self.PlusDwell = QtWidgets.QPushButton(self.centralwidget)
        self.PlusDwell.setGeometry(QtCore.QRect(530, 240, 251, 111))
        font = QtGui.QFont()
        font.setPointSize(48)
        self.PlusDwell.setFont(font)
        self.PlusDwell.setObjectName("PlusDwell")

        self.PlusSpeed = QtWidgets.QPushButton(self.centralwidget)
        self.PlusSpeed.setGeometry(QtCore.QRect(10, 240, 250, 111))
        font = QtGui.QFont()
        font.setPointSize(48)
        self.PlusSpeed.setFont(font)
        self.PlusSpeed.setObjectName("PlusSpeed")

        self.PlusDOR = QtWidgets.QPushButton(self.centralwidget)
        self.PlusDOR.setGeometry(QtCore.QRect(270, 240, 250, 111))
        font = QtGui.QFont()
        font.setPointSize(48)
        self.PlusDOR.setFont(font)
        self.PlusDOR.setObjectName("PlusDOR")

        self.line_horiz_motor = QtWidgets.QFrame(self.centralwidget)
        self.line_horiz_motor.setGeometry(QtCore.QRect(0, 170, 800, 20))
        self.line_horiz_motor.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_horiz_motor.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_horiz_motor.setObjectName("line_horiz_motor")

        self.MinusDOR = QtWidgets.QPushButton(self.centralwidget)
        self.MinusDOR.setGeometry(QtCore.QRect(270, 360, 250, 111))
        font = QtGui.QFont()
        font.setPointSize(48)
        self.MinusDOR.setFont(font)
        self.MinusDOR.setObjectName("MinusDOR")

        self.MinusDwell = QtWidgets.QPushButton(self.centralwidget)
        self.MinusDwell.setGeometry(QtCore.QRect(530, 360, 250, 111))
        font = QtGui.QFont()
        font.setPointSize(48)
        self.MinusDwell.setFont(font)
        self.MinusDwell.setObjectName("MinusDwell")

        self.DwellLabel = QtWidgets.QLabel(self.centralwidget)
        self.DwellLabel.setGeometry(QtCore.QRect(530, 190, 251, 41))
        font = QtGui.QFont()
        font.setPointSize(16)
        self.DwellLabel.setFont(font)
        self.DwellLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.DwellLabel.setObjectName("DwellLabel")

        self.dorSpinBox = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.dorSpinBox.setGeometry(QtCore.QRect(540, 60, 111, 51))
        self.dorSpinBox = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.dorSpinBox.setGeometry(QtCore.QRect(540, 60, 111, 51))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.PlaceholderText, brush)
        self.dorSpinBox.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(38)
        font.setBold(True)
        font.setWeight(75)
        self.dorSpinBox.setFont(font)
        self.dorSpinBox.setInputMethodHints(QtCore.Qt.ImhFormattedNumbersOnly)
        self.dorSpinBox.setFrame(False)
        self.dorSpinBox.setAlignment(QtCore.Qt.AlignCenter)
        self.dorSpinBox.setReadOnly(False)
        self.dorSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.dorSpinBox.setDecimals(0)
        self.dorSpinBox.setMaximum(360.0)
        self.dorSpinBox.setSingleStep(15.0)
        self.dorSpinBox.setProperty("value", 360.0)
        self.dorSpinBox.setObjectName("dorSpinBox")

        self.Motor_dor_label = QtWidgets.QLabel(self.centralwidget)
        self.Motor_dor_label.setGeometry(QtCore.QRect(270, 70, 271, 41))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(20)
        self.Motor_dor_label.setFont(font)
        self.Motor_dor_label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.Motor_dor_label.setObjectName("Motor_dor_label")

        self.dor_deg_label = QtWidgets.QLabel(self.centralwidget)
        self.dor_deg_label.setGeometry(QtCore.QRect(660, 80, 51, 31))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(14)
        self.dor_deg_label.setFont(font)
        self.dor_deg_label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.dor_deg_label.setObjectName("dor_deg_label")
        
        self.setCentralWidget(self.centralwidget)

        self.retranslateUi(self)
        QtCore.QMetaObject.connectSlotsByName(self)
        self.setWindowFlags(Qt.FramelessWindowHint)     # Makes window frameless for fullscreen

        # Connecting Signals/Slots
        self.SaveAndCloseMotor.clicked.connect(self.SaCM)
        self.PlusSpeed.clicked.connect(self.ps)
        self.PlusDOR.clicked.connect(self.pdor)
        self.PlusDwell.clicked.connect(self.pd)
        self.MinusSpeed.clicked.connect(self.ms)
        self.MinusDOR.clicked.connect(self.mdor)
        self.MinusDwell.clicked.connect(self.md)

    def retranslateUi(self, MotorWindow):
        _translate = QtCore.QCoreApplication.translate
        MotorWindow.setWindowTitle(_translate("Motor Settings", "Motor Settings"))
        self.deg_sec_label.setText(_translate("Motor Settings", "(deg/sec)"))
        self.Motor_dwell_label.setText(_translate("Motor Settings", "Dwell Time"))
        self.Motor_speed_label.setText(_translate("Motor Settings", "Speed"))
        self.SaveAndCloseMotor.setText(_translate("Motor Settings", "Save Settings and Close"))
        self.dwell_sec_label.setText(_translate("Motor Settings", "(sec)"))
        self.SpeedLabel.setText(_translate("Motor Settings", "Motor Speed +/- [15]"))
        self.MinusSpeed.setText(_translate("Motor Settings", "-"))
        self.DORLabel.setText(_translate("Motor Settings", "Degrees of Rotation +/- [45]"))
        self.PlusDwell.setText(_translate("Motor Settings", "+"))
        self.PlusSpeed.setText(_translate("Motor Settings", "+"))
        self.PlusDOR.setText(_translate("Motor Settings", "+"))
        self.MinusDOR.setText(_translate("Motor Settings", "-"))
        self.MinusDwell.setText(_translate("Motor Settings", "-"))
        self.DwellLabel.setText(_translate("Motor Settings", "Dwell Time +/- [0.5]"))
        self.Motor_dor_label.setText(_translate("Motor Settings", "Degrees of Rotation"))
        self.dor_deg_label.setText(_translate("Motor Settings", "(deg)"))
    
    # SaCM - Saves motor settings and sends changes to main screen
    def SaCM(self):
        self.saveMotorSettings.emit()
        log.debug("Closing Motor Settings window")
        self.hide()

    # Functions below add or subtract from each double spinbox

    def ps(self):
        self.msSpinBox.stepUp()
    
    def pdor(self):
        self.dorSpinBox.stepUp()

    def pd(self):
        self.dwellSpinBox.stepUp()

    def ms(self):
        self.msSpinBox.stepDown()
    
    def mdor(self):
        self.dorSpinBox.stepDown()

    def md(self):
        self.dwellSpinBox.stepDown()

# --------------------------------
# GenWindow creates the General Settings window
# --------------------------------
class GenWindow(QMainWindow):

    saveGenSettings = pyqtSignal()     # Signal used to save settings upon "Save Settings and Close"

    def __init__(self):
        super(GenWindow, self).__init__()
        self.setGeometry(0, 0, 800, 480)
        self.initUI()

    def initUI(self):
        self.setObjectName("Gen Settings")
        self.resize(800, 480)

        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 128))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.PlaceholderText, brush)
        self.setPalette(palette)
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.setTabShape(QtWidgets.QTabWidget.Rounded)
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")

        self.graphicsView_Graph_settings = QtWidgets.QGraphicsView(self.centralwidget)
        self.graphicsView_Graph_settings.setGeometry(QtCore.QRect(0, 0, 261, 181))
        self.graphicsView_Graph_settings.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.graphicsView_Graph_settings.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.graphicsView_Graph_settings.setObjectName("graphicsView_Graph_settings")

        self.line_vert_graph_set = QtWidgets.QFrame(self.centralwidget)
        self.line_vert_graph_set.setGeometry(QtCore.QRect(250, 0, 20, 181))
        self.line_vert_graph_set.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_vert_graph_set.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_vert_graph_set.setObjectName("line_vert_graph_set")

        self.SaveAndCloseGen = QtWidgets.QPushButton(self.centralwidget)
        self.SaveAndCloseGen.setGeometry(QtCore.QRect(20, 20, 221, 141))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(13)
        self.SaveAndCloseGen.setFont(font)
        self.SaveAndCloseGen.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.SaveAndCloseGen.setObjectName("SaveAndCloseGen")

        self.Enable_label = QtWidgets.QLabel(self.centralwidget)
        self.Enable_label.setGeometry(QtCore.QRect(400, 10, 251, 51))
        font = QtGui.QFont()
        font.setFamily("Leelawadee")
        font.setPointSize(24)
        self.Enable_label.setFont(font)
        self.Enable_label.setAlignment(QtCore.Qt.AlignCenter)
        self.Enable_label.setObjectName("Enable_label")

        self.line_horiz_graph_set = QtWidgets.QFrame(self.centralwidget)
        self.line_horiz_graph_set.setGeometry(QtCore.QRect(0, 170, 261, 20))
        self.line_horiz_graph_set.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_horiz_graph_set.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_horiz_graph_set.setObjectName("line_horiz_graph_set")

        self.Enable_on_B = QtWidgets.QPushButton(self.centralwidget)
        self.Enable_on_B.setGeometry(QtCore.QRect(300, 60, 221, 91))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(15)
        self.Enable_on_B.setFont(font)
        self.Enable_on_B.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.Enable_on_B.setCheckable(True)
        self.Enable_on_B.setChecked(True)
        self.Enable_on_B.setObjectName("Enable_on_B")

        self.Enable_off_B = QtWidgets.QPushButton(self.centralwidget)
        self.Enable_off_B.setGeometry(QtCore.QRect(530, 60, 221, 91))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(15)
        self.Enable_off_B.setFont(font)
        self.Enable_off_B.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.Enable_off_B.setCheckable(True)
        self.Enable_off_B.setObjectName("Enable_off_B")

        self.Rotate_setting_label = QtWidgets.QLabel(self.centralwidget)
        self.Rotate_setting_label.setGeometry(QtCore.QRect(370, 150, 321, 51))
        font = QtGui.QFont()
        font.setFamily("Leelawadee")
        font.setPointSize(24)
        self.Rotate_setting_label.setFont(font)
        self.Rotate_setting_label.setAlignment(QtCore.Qt.AlignCenter)
        self.Rotate_setting_label.setObjectName("Rotate_setting_label")
        self.Toggle_B = QtWidgets.QPushButton(self.centralwidget)
        self.Toggle_B.setGeometry(QtCore.QRect(530, 200, 221, 91))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(15)
        self.Toggle_B.setFont(font)
        self.Toggle_B.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.Toggle_B.setCheckable(True)
        self.Toggle_B.setObjectName("Toggle_B")

        self.Click_B = QtWidgets.QPushButton(self.centralwidget)
        self.Click_B.setGeometry(QtCore.QRect(300, 200, 221, 91))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(15)
        self.Click_B.setFont(font)
        self.Click_B.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.Click_B.setCheckable(True)
        self.Click_B.setChecked(True)
        self.Click_B.setObjectName("Click_B")

        self.Alarm_label = QtWidgets.QLabel(self.centralwidget)
        self.Alarm_label.setGeometry(QtCore.QRect(430, 300, 201, 51))
        font = QtGui.QFont()
        font.setFamily("Leelawadee")
        font.setPointSize(24)
        self.Alarm_label.setFont(font)
        self.Alarm_label.setAlignment(QtCore.Qt.AlignCenter)
        self.Alarm_label.setObjectName("Alarm_label")

        self.Exit_B = QtWidgets.QPushButton(self.centralwidget)
        self.Exit_B.setGeometry(QtCore.QRect(10, 400, 211, 71))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(15)
        self.Exit_B.setFont(font)
        self.Exit_B.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.Exit_B.setCheckable(False)
        self.Exit_B.setChecked(False)
        self.Exit_B.setObjectName("Exit_B")

        self.textBrowser = QtWidgets.QTextBrowser(self.centralwidget)
        self.textBrowser.setGeometry(QtCore.QRect(300, 350, 461, 121))
        font.setPointSize(9)
        self.textBrowser.setFont(font)
        self.textBrowser.setObjectName("textBrowser")

        self.Alarm_stat_graphicsView = QtWidgets.QGraphicsView(self.centralwidget)
        self.Alarm_stat_graphicsView.setGeometry(QtCore.QRect(630, 310, 51, 31))
        self.Alarm_stat_graphicsView.setObjectName("Alarm_stat_graphicsView")
        self.setCentralWidget(self.centralwidget)

        self.retranslateUi(self)
        QtCore.QMetaObject.connectSlotsByName(self)
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Connecting Signals/Slots
        self.SaveAndCloseGen.clicked.connect(self.SaCG)

        self.Enable_on_B.clicked.connect(self.G_on)
        self.Enable_off_B.clicked.connect(self.G_off)

        self.Click_B.clicked.connect(self.Rot_C)
        self.Toggle_B.clicked.connect(self.Rot_T)

        self.Exit_B.clicked.connect(self.closeGUI)


    def retranslateUi(self, GenWindow):
        _translate = QtCore.QCoreApplication.translate
        GenWindow.setWindowTitle(_translate("General Settings", "General Settings"))
        self.SaveAndCloseGen.setText(_translate("General Settings", "Save Settings and Close"))
        self.Enable_label.setText(_translate("General Settings", "Enable Graph"))
        self.Enable_on_B.setText(_translate("General Settings", "On"))
        self.Enable_off_B.setText(_translate("General Settings", "Off"))
        self.Rotate_setting_label.setText(_translate("General Settings", "Rotate Setting"))
        self.Toggle_B.setText(_translate("General Settings", "Toggle"))
        self.Click_B.setText(_translate("General Settings", "Click"))
        self.Alarm_label.setText(_translate("General Settings", "Alarm Status"))
        self.Exit_B.setText(_translate("General Settings", "Exit GUI"))


    # SaCG - Saves general settings and sends changes to main screen
    def SaCG(self):
        self.saveGenSettings.emit()
        log.info("Closing General Settings window")
        self.hide()

    # G_on & G_off enables or disables the graph on main screen
    def G_on(self):
        self.Enable_on_B.setChecked(True)
        self.Enable_off_B.setChecked(False)

    def G_off(self):
        self.Enable_off_B.setChecked(True)
        self.Enable_on_B.setChecked(False)

    # Rot_C & Rot_T determine if rotate is toggleable or clickable
    def Rot_C(self):
        self.Click_B.setChecked(True)
        self.Toggle_B.setChecked(False)

    def Rot_T(self):
        self.Toggle_B.setChecked(True)
        self.Click_B.setChecked(False)

    # closeGUI exits Python program
    def closeGUI(self):
        log.info("Exiting program")
        sys.exit(app.exec())

# --------------------------------
# TempWindow creates the Temperature Settings window
# --------------------------------
class TempWindow(QMainWindow):

    saveTempSettings = pyqtSignal()     # Signal used to save settings upon "Save Settings and Close"

    def __init__(self):
        super(TempWindow, self).__init__()
        self.setGeometry(0, 0, 800, 480)
        self.initUI()

    def initUI(self):
        self.setObjectName("Temperature Settings")
        self.resize(800, 480)

        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.PlaceholderText, brush)
        self.setPalette(palette)
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.setTabShape(QtWidgets.QTabWidget.Rounded)
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")

        self.st_label = QtWidgets.QLabel(self.centralwidget)
        self.st_label.setGeometry(QtCore.QRect(360, 70, 271, 41))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(24)
        self.st_label.setFont(font)
        self.st_label.setAlignment(QtCore.Qt.AlignCenter)
        self.st_label.setObjectName("st_label")

        self.graphicsView_temp = QtWidgets.QGraphicsView(self.centralwidget)
        self.graphicsView_temp.setGeometry(QtCore.QRect(0, 0, 261, 181))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        self.graphicsView_temp.setPalette(palette)
        self.graphicsView_temp.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.graphicsView_temp.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.graphicsView_temp.setObjectName("graphicsView_temp")

        self.line_vert_temp = QtWidgets.QFrame(self.centralwidget)
        self.line_vert_temp.setGeometry(QtCore.QRect(250, 0, 20, 181))
        self.line_vert_temp.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_vert_temp.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_vert_temp.setObjectName("line_vert_temp")

        self.SaveAndCloseTemp = QtWidgets.QPushButton(self.centralwidget)
        self.SaveAndCloseTemp.setGeometry(QtCore.QRect(20, 20, 221, 141))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(13)
        self.SaveAndCloseTemp.setFont(font)
        self.SaveAndCloseTemp.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.SaveAndCloseTemp.setObjectName("SaveAndCloseTemp")

        self.label10 = QtWidgets.QLabel(self.centralwidget)
        self.label10.setGeometry(QtCore.QRect(10, 200, 187, 31))
        font = QtGui.QFont()
        font.setPointSize(18)
        self.label10.setFont(font)
        self.label10.setAlignment(QtCore.Qt.AlignCenter)
        self.label10.setObjectName("label10")

        self.minus10 = QtWidgets.QPushButton(self.centralwidget)
        self.minus10.setGeometry(QtCore.QRect(10, 360, 187, 111))
        font = QtGui.QFont()
        font.setPointSize(48)
        self.minus10.setFont(font)
        self.minus10.setObjectName("minus10")

        self.label1 = QtWidgets.QLabel(self.centralwidget)
        self.label1.setGeometry(QtCore.QRect(207, 200, 187, 31))
        font = QtGui.QFont()
        font.setPointSize(18)
        self.label1.setFont(font)
        self.label1.setAlignment(QtCore.Qt.AlignCenter)
        self.label1.setObjectName("label1")

        self.plus01 = QtWidgets.QPushButton(self.centralwidget)
        self.plus01.setGeometry(QtCore.QRect(404, 240, 187, 111))
        font = QtGui.QFont()
        font.setPointSize(48)
        self.plus01.setFont(font)
        self.plus01.setObjectName("plus01")

        self.plus10 = QtWidgets.QPushButton(self.centralwidget)
        self.plus10.setGeometry(QtCore.QRect(10, 240, 187, 111))
        font = QtGui.QFont()
        font.setPointSize(48)
        self.plus10.setFont(font)
        self.plus10.setObjectName("plus10")

        self.plus1 = QtWidgets.QPushButton(self.centralwidget)
        self.plus1.setGeometry(QtCore.QRect(207, 240, 187, 111))
        font = QtGui.QFont()
        font.setPointSize(48)
        self.plus1.setFont(font)
        self.plus1.setObjectName("plus1")

        self.line_horiz_motor = QtWidgets.QFrame(self.centralwidget)
        self.line_horiz_motor.setGeometry(QtCore.QRect(0, 170, 800, 20))
        self.line_horiz_motor.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_horiz_motor.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_horiz_motor.setObjectName("line_horiz_motor")

        self.minus1 = QtWidgets.QPushButton(self.centralwidget)
        self.minus1.setGeometry(QtCore.QRect(207, 360, 187, 111))
        font = QtGui.QFont()
        font.setPointSize(48)
        self.minus1.setFont(font)
        self.minus1.setObjectName("minus1")

        self.minus01 = QtWidgets.QPushButton(self.centralwidget)
        self.minus01.setGeometry(QtCore.QRect(404, 360, 187, 111))
        font = QtGui.QFont()
        font.setPointSize(48)
        self.minus01.setFont(font)
        self.minus01.setObjectName("minus01")

        self.currentSpinBox = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.currentSpinBox.setGeometry(QtCore.QRect(430, 30, 121, 41))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.PlaceholderText, brush)
        self.currentSpinBox.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(28)
        font.setBold(True)
        font.setWeight(75)
        self.currentSpinBox.setFont(font)
        self.currentSpinBox.setInputMethodHints(QtCore.Qt.ImhFormattedNumbersOnly)
        self.currentSpinBox.setFrame(False)
        self.currentSpinBox.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.currentSpinBox.setReadOnly(False)
        self.currentSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.currentSpinBox.setDecimals(2)
        self.currentSpinBox.setMaximum(99.99)
        self.currentSpinBox.setSingleStep(1.0)
        self.currentSpinBox.setProperty("value", 0.0)
        self.currentSpinBox.setObjectName("currentSpinBox")

        self.ct_label = QtWidgets.QLabel(self.centralwidget)
        self.ct_label.setGeometry(QtCore.QRect(360, 0, 301, 41))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(18)
        self.ct_label.setFont(font)
        self.ct_label.setAlignment(QtCore.Qt.AlignCenter)
        self.ct_label.setObjectName("ct_label")
        self.c1_label = QtWidgets.QLabel(self.centralwidget)
        self.c1_label.setGeometry(QtCore.QRect(550, 30, 21, 21))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.PlaceholderText, brush)
        self.c1_label.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(13)
        self.c1_label.setFont(font)
        self.c1_label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.c1_label.setObjectName("c1_label")

        self.setSpinBox = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.setSpinBox.setGeometry(QtCore.QRect(390, 110, 181, 51))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.PlaceholderText, brush)
        self.setSpinBox.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(42)
        font.setBold(True)
        font.setWeight(75)
        self.setSpinBox.setFont(font)
        self.setSpinBox.setInputMethodHints(QtCore.Qt.ImhFormattedNumbersOnly)
        self.setSpinBox.setFrame(False)
        self.setSpinBox.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.setSpinBox.setReadOnly(False)
        self.setSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.setSpinBox.setDecimals(2)
        self.setSpinBox.setMaximum(40.0)
        self.setSpinBox.setSingleStep(1.0)
        self.setSpinBox.setProperty("value", 0.0)
        self.setSpinBox.setObjectName("setSpinBox")

        self.c2_label = QtWidgets.QLabel(self.centralwidget)
        self.c2_label.setGeometry(QtCore.QRect(570, 110, 21, 21))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.PlaceholderText, brush)
        self.c2_label.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(15)
        self.c2_label.setFont(font)
        self.c2_label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.c2_label.setObjectName("c2_label")

        self.plus001 = QtWidgets.QPushButton(self.centralwidget)
        self.plus001.setGeometry(QtCore.QRect(601, 240, 187, 111))
        font = QtGui.QFont()
        font.setPointSize(48)
        self.plus001.setFont(font)
        self.plus001.setObjectName("plus001")

        self.minus001 = QtWidgets.QPushButton(self.centralwidget)
        self.minus001.setGeometry(QtCore.QRect(601, 360, 187, 111))
        font = QtGui.QFont()
        font.setPointSize(48)
        self.minus001.setFont(font)
        self.minus001.setObjectName("minus001")

        self.label01 = QtWidgets.QLabel(self.centralwidget)
        self.label01.setGeometry(QtCore.QRect(404, 200, 187, 31))
        font = QtGui.QFont()
        font.setPointSize(18)
        self.label01.setFont(font)
        self.label01.setAlignment(QtCore.Qt.AlignCenter)
        self.label01.setObjectName("label01")

        self.label001 = QtWidgets.QLabel(self.centralwidget)
        self.label001.setGeometry(QtCore.QRect(601, 200, 187, 31))
        font = QtGui.QFont()
        font.setPointSize(18)
        self.label001.setFont(font)
        self.label001.setAlignment(QtCore.Qt.AlignCenter)
        self.label001.setObjectName("label001")
        """
        self.graphicsView_temp.raise_()
        self.line_vert_temp.raise_()
        self.st_label.raise_()
        self.SaveAndCloseTemp.raise_()
        self.label10.raise_()
        self.minus10.raise_()
        self.label1.raise_()
        self.plus01.raise_()
        self.plus10.raise_()
        self.plus1.raise_()
        self.line_horiz_motor.raise_()
        self.minus1.raise_()
        self.minus01.raise_()
        self.currentSpinBox.raise_()
        self.ct_label.raise_()
        self.c1_label.raise_()
        self.setSpinBox.raise_()
        self.c2_label.raise_()
        self.plus001.raise_()
        self.minus001.raise_()
        self.label01.raise_()
        self.label001.raise_()
        """
        self.setCentralWidget(self.centralwidget)

        self.retranslateUi(self)
        QtCore.QMetaObject.connectSlotsByName(self)
        self.setWindowFlags(Qt.FramelessWindowHint)     # Makes window frameless for fullscreen

        # Connecting Signals/Slots
        self.plus10.clicked.connect(self.p10)
        self.plus1.clicked.connect(self.p1)
        self.plus01.clicked.connect(self.p01)
        self.plus001.clicked.connect(self.p001)
        self.minus10.clicked.connect(self.m10)
        self.minus1.clicked.connect(self.m1)
        self.minus01.clicked.connect(self.m01)
        self.minus001.clicked.connect(self.m001)

        self.SaveAndCloseTemp.clicked.connect(self.SaCT)

    def retranslateUi(self, TempWindow):
        _translate = QtCore.QCoreApplication.translate
        TempWindow.setWindowTitle(_translate("Temperature Settings", "Temperature Settings"))
        self.st_label.setText(_translate("Temperature Settings", "Set Temperature"))
        self.SaveAndCloseTemp.setText(_translate("Temperature Settings", "Save Settings and Close"))
        self.label10.setText(_translate("Temperature Settings", "+/- 10"))
        self.minus10.setText(_translate("Temperature Settings", "-"))
        self.label1.setText(_translate("Temperature Settings", "+/- 1"))
        self.plus01.setText(_translate("Temperature Settings", "+"))
        self.plus10.setText(_translate("Temperature Settings", "+"))
        self.plus1.setText(_translate("Temperature Settings", "+"))
        self.minus1.setText(_translate("Temperature Settings", "-"))
        self.minus01.setText(_translate("Temperature Settings", "-"))
        self.ct_label.setText(_translate("Temperature Settings", "Current Temperature"))
        self.c1_label.setText(_translate("Temperature Settings", "C"))
        self.c2_label.setText(_translate("Temperature Settings", "C"))
        self.plus001.setText(_translate("Temperature Settings", "+"))
        self.minus001.setText(_translate("Temperature Settings", "-"))
        self.label01.setText(_translate("Temperature Settings", "+/- 0.1"))
        self.label001.setText(_translate("Temperature Settings", "+/- 0.01"))

    # SaCT - Saves temperature settings and sends changes to main screen
    def SaCT(self):                 # hide window and update main window
        self.saveTempSettings.emit()
        log.debug("Closing Temperature Settings Window")
        self.hide()

    # Functions below add or subtract from set temp at different increments
    def p10(self):
        self.setSpinBox.setSingleStep(10.0)
        self.setSpinBox.stepUp()

    def p1(self):
        self.setSpinBox.setSingleStep(1.0)
        self.setSpinBox.stepUp()
    
    def p01(self):
        self.setSpinBox.setSingleStep(0.1)
        self.setSpinBox.stepUp()

    def p001(self):
        self.setSpinBox.setSingleStep(0.01)
        self.setSpinBox.stepUp()
    
    def m10(self):
        self.setSpinBox.setSingleStep(10.0)
        self.setSpinBox.stepDown()

    def m1(self):
        self.setSpinBox.setSingleStep(1.0)
        self.setSpinBox.stepDown()
    
    def m01(self):
        self.setSpinBox.setSingleStep(0.1)
        self.setSpinBox.stepDown()

    def m001(self):
        self.setSpinBox.setSingleStep(0.01)
        self.setSpinBox.stepDown()

# --------------------------------
# MyWindow is the main window in which the program runs
# --------------------------------
class MyWindow(QMainWindow):        # can name MyWindow anything, inherit QMainWindow class

    alarm_info = pyqtSignal()       # alarm signal sends data to general settings window if alarms are triggered

    def __init__(self):
        super(MyWindow, self).__init__()        #super refrences top lvl class
        self.setGeometry(0, 0, 800, 480)
        self.initUI()

    def initUI(self):
        self.setObjectName("MainWindow")
        self.resize(800, 480)

        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 128))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(54, 54, 54))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 128))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 128))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.PlaceholderText, brush)
        self.setPalette(palette)
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.setTabShape(QtWidgets.QTabWidget.Rounded)
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")

        self.ST_SB = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.ST_SB.setGeometry(QtCore.QRect(550, 50, 221, 71))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        self.ST_SB.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(52)
        font.setBold(True)
        font.setWeight(75)
        self.ST_SB.setFont(font)
        self.ST_SB.setInputMethodHints(QtCore.Qt.ImhFormattedNumbersOnly)
        self.ST_SB.setFrame(False)
        self.ST_SB.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.ST_SB.setReadOnly(False)
        self.ST_SB.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.ST_SB.setDecimals(2)
        self.ST_SB.setMaximum(40.0) 
        self.ST_SB.setSingleStep(1.0)
        self.ST_SB.setObjectName("ST_SB")

        self.Set_temp_label = QtWidgets.QLabel(self.centralwidget)
        self.Set_temp_label.setGeometry(QtCore.QRect(580, 20, 161, 31))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(14)
        self.Set_temp_label.setFont(font)
        self.Set_temp_label.setAlignment(QtCore.Qt.AlignCenter)
        self.Set_temp_label.setObjectName("Set_temp_label")

        self.CT_SB = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.CT_SB.setGeometry(QtCore.QRect(270, 40, 251, 71))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        self.CT_SB.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(58)
        font.setBold(True)
        font.setWeight(75)
        self.CT_SB.setFont(font)
        self.CT_SB.setInputMethodHints(QtCore.Qt.ImhFormattedNumbersOnly)
        self.CT_SB.setFrame(False)
        self.CT_SB.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.CT_SB.setReadOnly(False)
        self.CT_SB.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.CT_SB.setDecimals(2)
        self.CT_SB.setSingleStep(1.00)
        self.CT_SB.setObjectName("CT_SB")

        self.deg_sec_label = QtWidgets.QLabel(self.centralwidget)
        self.deg_sec_label.setGeometry(QtCore.QRect(450, 210, 101, 31))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(14)
        self.deg_sec_label.setFont(font)
        self.deg_sec_label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.deg_sec_label.setObjectName("deg_sec_label")

        self.Motor_dor_label = QtWidgets.QLabel(self.centralwidget)
        self.Motor_dor_label.setGeometry(QtCore.QRect(540, 135, 191, 21))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(13)
        self.Motor_dor_label.setFont(font)
        self.Motor_dor_label.setAlignment(QtCore.Qt.AlignCenter)
        self.Motor_dor_label.setObjectName("Motor_dor_label")
        self.Motor_dwell_label = QtWidgets.QLabel(self.centralwidget)
        self.Motor_dwell_label.setGeometry(QtCore.QRect(590, 192, 101, 21))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(13)
        self.Motor_dwell_label.setFont(font)
        self.Motor_dwell_label.setAlignment(QtCore.Qt.AlignCenter)
        self.Motor_dwell_label.setObjectName("Motor_dwell_label")

        self.MS_SB = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.MS_SB.setGeometry(QtCore.QRect(270, 170, 181, 71))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        self.MS_SB.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(58)
        font.setWeight(75)
        self.MS_SB.setFont(font)
        self.MS_SB.setInputMethodHints(QtCore.Qt.ImhFormattedNumbersOnly)
        self.MS_SB.setFrame(False)
        self.MS_SB.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.MS_SB.setReadOnly(False)
        self.MS_SB.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.MS_SB.setDecimals(0)
        self.MS_SB.setMaximum(360.0)                            #
        self.MS_SB.setSingleStep(1.0)
        self.MS_SB.setProperty("value", 90.0)
        self.MS_SB.setObjectName("MS_SB")

        self.MDOR_SB = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.MDOR_SB.setGeometry(QtCore.QRect(570, 155, 101, 31))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        self.MDOR_SB.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(28)
        font.setBold(True)
        font.setWeight(75)
        self.MDOR_SB.setFont(font)
        self.MDOR_SB.setInputMethodHints(QtCore.Qt.ImhFormattedNumbersOnly)
        self.MDOR_SB.setFrame(False)
        self.MDOR_SB.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.MDOR_SB.setReadOnly(False)
        self.MDOR_SB.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.MDOR_SB.setDecimals(0)
        self.MDOR_SB.setMaximum(360.0)
        self.MDOR_SB.setSingleStep(15.0)
        self.MDOR_SB.setProperty("value", 360.0)
        self.MDOR_SB.setObjectName("MDOR_SB")

        self.MD_SB = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.MD_SB.setGeometry(QtCore.QRect(560, 212, 111, 31))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        self.MD_SB.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(28)
        font.setBold(True)
        font.setWeight(75)
        self.MD_SB.setFont(font)
        self.MD_SB.setInputMethodHints(QtCore.Qt.ImhFormattedNumbersOnly)
        self.MD_SB.setFrame(False)
        self.MD_SB.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.MD_SB.setReadOnly(False)
        self.MD_SB.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.MD_SB.setDecimals(1)
        self.MD_SB.setMaximum(10.0)
        self.MD_SB.setSingleStep(0.5)
        self.MD_SB.setProperty("value", 0.5)
        self.MD_SB.setObjectName("MD_SB")

        self.graphicsView = QtWidgets.QGraphicsView(self.centralwidget)
        self.graphicsView.setGeometry(QtCore.QRect(0, 0, 261, 481))
        self.graphicsView.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.graphicsView.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.graphicsView.setObjectName("graphicsView")

        self.line_vert = QtWidgets.QFrame(self.centralwidget)
        self.line_vert.setGeometry(QtCore.QRect(250, 0, 20, 491))
        self.line_vert.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_vert.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_vert.setObjectName("line_vert")

        self.line_horiz = QtWidgets.QFrame(self.centralwidget)
        self.line_horiz.setGeometry(QtCore.QRect(330, 120, 401, 20))
        self.line_horiz.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_horiz.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_horiz.setObjectName("line_horiz")

        self.Current_temp_label = QtWidgets.QLabel(self.centralwidget)
        self.Current_temp_label.setGeometry(QtCore.QRect(290, 0, 191, 41))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(22)
        self.Current_temp_label.setFont(font)
        self.Current_temp_label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.Current_temp_label.setObjectName("Current_temp_label")

        self.Motor_speed_label = QtWidgets.QLabel(self.centralwidget)
        self.Motor_speed_label.setGeometry(QtCore.QRect(290, 130, 101, 41))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(23)
        self.Motor_speed_label.setFont(font)
        self.Motor_speed_label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.Motor_speed_label.setObjectName("Motor_speed_label")

        self.ct_c_label = QtWidgets.QLabel(self.centralwidget)
        self.ct_c_label.setGeometry(QtCore.QRect(520, 40, 21, 31))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(18)
        self.ct_c_label.setFont(font)
        self.ct_c_label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.ct_c_label.setObjectName("ct_c_label")

        self.st_c_label = QtWidgets.QLabel(self.centralwidget)
        self.st_c_label.setGeometry(QtCore.QRect(770, 50, 21, 31))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(15)
        self.st_c_label.setFont(font)
        self.st_c_label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.st_c_label.setObjectName("st_c_label")

        self.dwell_sec_label = QtWidgets.QLabel(self.centralwidget)
        self.dwell_sec_label.setGeometry(QtCore.QRect(670, 222, 41, 21))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(13)
        self.dwell_sec_label.setFont(font)
        self.dwell_sec_label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.dwell_sec_label.setObjectName("dwell_sec_label")

        self.dor_deg_label = QtWidgets.QLabel(self.centralwidget)
        self.dor_deg_label.setGeometry(QtCore.QRect(670, 165, 51, 21))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(13)
        self.dor_deg_label.setFont(font)
        self.dor_deg_label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.dor_deg_label.setObjectName("dor_deg_label")

        self.line_horiz_graph = QtWidgets.QFrame(self.centralwidget)
        self.line_horiz_graph.setGeometry(QtCore.QRect(260, 240, 540, 16))
        self.line_horiz_graph.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_horiz_graph.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_horiz_graph.setObjectName("line_horiz_graph")

        self.MotorSettings_B = QtWidgets.QPushButton(self.centralwidget)
        self.MotorSettings_B.setGeometry(QtCore.QRect(20, 300, 221, 81))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(15)
        self.MotorSettings_B.setFont(font)
        self.MotorSettings_B.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.MotorSettings_B.setAutoFillBackground(False)
        self.MotorSettings_B.setObjectName("MotorSettings_B")

        self.Rotate_label = QtWidgets.QLabel(self.centralwidget)
        self.Rotate_label.setGeometry(QtCore.QRect(100, 120, 91, 31))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(18)
        self.Rotate_label.setFont(font)
        self.Rotate_label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.Rotate_label.setObjectName("Rotate_label")

        self.StartStopMotor_B = QtWidgets.QPushButton(self.centralwidget)
        self.StartStopMotor_B.setGeometry(QtCore.QRect(20, 30, 221, 91))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(15)
        self.StartStopMotor_B.setFont(font)
        self.StartStopMotor_B.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.StartStopMotor_B.setCheckable(True)
        self.StartStopMotor_B.setObjectName("StartStopMotor_B")

        self.RotateRev_B = QtWidgets.QPushButton(self.centralwidget)
        self.RotateRev_B.setGeometry(QtCore.QRect(20, 150, 101, 61))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(15)
        self.RotateRev_B.setFont(font)
        self.RotateRev_B.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.RotateRev_B.setObjectName("RotateRev_B")

        self.TempSettings_B = QtWidgets.QPushButton(self.centralwidget)
        self.TempSettings_B.setGeometry(QtCore.QRect(20, 220, 221, 81))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(15)
        self.TempSettings_B.setFont(font)
        self.TempSettings_B.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.TempSettings_B.setObjectName("TempSettings_B")

        self.RotateFwd_B = QtWidgets.QPushButton(self.centralwidget)
        self.RotateFwd_B.setGeometry(QtCore.QRect(140, 150, 101, 61))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(15)
        self.RotateFwd_B.setFont(font)
        self.RotateFwd_B.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.RotateFwd_B.setObjectName("RotateFwd_B")

        self.Motor_label = QtWidgets.QLabel(self.centralwidget)
        self.Motor_label.setGeometry(QtCore.QRect(100, 0, 81, 31))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(18)
        self.Motor_label.setFont(font)
        self.Motor_label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.Motor_label.setObjectName("Motor_label")
        
        self.GenSettings_B = QtWidgets.QPushButton(self.centralwidget)
        self.GenSettings_B.setGeometry(QtCore.QRect(20, 390, 121, 81))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(10)
        self.GenSettings_B.setFont(font)
        self.GenSettings_B.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.GenSettings_B.setObjectName("GenSettings_B")

        self.Alarm_status_label = QtWidgets.QLabel(self.centralwidget)
        self.Alarm_status_label.setGeometry(QtCore.QRect(140, 390, 121, 31))
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        font.setPointSize(11)
        self.Alarm_status_label.setFont(font)
        self.Alarm_status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.Alarm_status_label.setObjectName("Alarm_status_label")

        self.alarm_graphicsView = QtWidgets.QGraphicsView(self.centralwidget)
        self.alarm_graphicsView.setGeometry(QtCore.QRect(150, 420, 101, 51))
        self.alarm_graphicsView.setObjectName("alarm_graphicsView")

        # Initialize graph using PyQtGraph
        self.temp_graph = PlotWidget(self.centralwidget)
        self.temp_graph.setGeometry(QtCore.QRect(270, 260, 521, 211))
        self.temp_graph.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.temp_graph.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.temp_graph.setBackground((43,43,43))
        self.temp_graph.setObjectName("temp_graph")
        styles = {'color':'#fff', 'font-size':'14px'}
        pen = mkPen(color=(255, 64, 64), width=3)
        self.temp_graph.getAxis('left').setPen('w')
        self.temp_graph.getAxis('bottom').setPen('w')
        self.temp_graph.getAxis('left').setTextPen('w')
        self.temp_graph.getAxis('bottom').setTextPen('w')
        self.x = [0.0] * 20
        self.y = [0.0] * 20
        self.temp_graph.setLabel('left', 'Temperature (°C)', **styles)
        self.temp_graph.setLabel('bottom', 'Time (sec)', **styles)
        self.data=self.temp_graph.plot(self.x, self.y, pen=pen)

        self.initTime = round(time.time(),1)
        self.yy = 0.0
        
        
        """
        self.MDOR_SB.raise_()
        self.graphicsView.raise_()
        self.ST_SB.raise_()
        self.Set_temp_label.raise_()
        self.CT_SB.raise_()
        self.deg_sec_label.raise_()
        self.Motor_dor_label.raise_()
        self.MS_SB.raise_()
        self.MD_SB.raise_()
        self.line_vert.raise_()
        self.line_horiz.raise_()
        self.Motor_speed_label.raise_()
        self.Current_temp_label.raise_()
        self.ct_c_label.raise_()
        self.Motor_dwell_label.raise_()
        self.st_c_label.raise_()
        self.dwell_sec_label.raise_()
        self.dor_deg_label.raise_()
        self.line_horiz_graph.raise_()
        #self.GRAPH.raise_()
        self.MotorSettings_B.raise_()
        self.Rotate_label.raise_()
        self.StartStopMotor_B.raise_()
        self.RotateRev_B.raise_()
        self.TempSettings_B.raise_()
        self.RotateFwd_B.raise_()
        self.Motor_label.raise_()
        self.GenSettings_B.raise_()
        """
        self.setCentralWidget(self.centralwidget)

        self.retranslateUi(self)
        QtCore.QMetaObject.connectSlotsByName(self)

        # Create Modbus server
        self.StartServer()

        # Create each settings window
        self.tempwindow = TempWindow()
        self.motorwindow = MotorWindow()
        self.genwindow = GenWindow()

        # Connecting Signals/Slots
        self.TempSettings_B.clicked.connect(self.tempclick)
        self.MotorSettings_B.clicked.connect(self.motorclick)
        self.GenSettings_B.clicked.connect(self.genclick)
        self.tempwindow.saveTempSettings.connect(self.updateST)     # on save aand close, updates main window
        self.motorwindow.saveMotorSettings.connect(self.updateMS)
        self.genwindow.saveGenSettings.connect(self.updateGenSettings)
        self.serverworker.updateModbusValues.connect(self.updateMB)
        self.serverworker.updateGUIValues.connect(self.updateMainGUIValues)
        self.serverworker.updateCurrentTemp.connect(self.updateGUICurrentTemp)
        self.serverworker.SendSetTemp.connect(self.send_temp_fromMB)
        self.serverworker.sendAlarmStatus.connect(self.updateAlarms)
        self.serverworker.setSetTemp.connect(self.initialSetTemp)
        self.serverworker.motorStatus.connect(self.modbusMotorChange)
        self.RotateFwd_B.clicked.connect(self.Forward)
        self.RotateRev_B.clicked.connect(self.Reverse)
        self.StartStopMotor_B.clicked.connect(self.StartStopHandler)

        self.setWindowFlags(Qt.FramelessWindowHint)                 # Makes window frameless for fullscreen
        
    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.Set_temp_label.setText(_translate("MainWindow", "Set Temperature"))
        self.deg_sec_label.setText(_translate("MainWindow", "(deg/sec)"))
        self.Motor_dor_label.setText(_translate("MainWindow", "Degrees of Rotation"))
        self.Motor_dwell_label.setText(_translate("MainWindow", "Dwell Time"))
        self.Current_temp_label.setText(_translate("MainWindow", "Temperature"))
        self.Motor_speed_label.setText(_translate("MainWindow", "Speed"))
        self.ct_c_label.setText(_translate("MainWindow", "C"))
        self.st_c_label.setText(_translate("MainWindow", "C"))
        self.dwell_sec_label.setText(_translate("MainWindow", "(sec)"))
        self.dor_deg_label.setText(_translate("MainWindow", "(deg)"))
        self.MotorSettings_B.setText(_translate("MainWindow", "Motor Settings"))
        self.Rotate_label.setText(_translate("MainWindow", "Rotate"))
        self.Alarm_status_label.setText(_translate("MainWindow", "Alarm Status"))
        self.StartStopMotor_B.setText(_translate("MainWindow", "Start / Stop"))
        self.RotateRev_B.setText(_translate("MainWindow", "Back"))
        self.TempSettings_B.setText(_translate("MainWindow", "Tempature Settings"))
        self.RotateFwd_B.setText(_translate("MainWindow", "Next"))
        self.Motor_label.setText(_translate("MainWindow", "Motor"))
        self.GenSettings_B.setText(_translate("MainWindow", "General Settings"))

    # Changes screen to show graph
    def withGraph(self):
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        self.deg_sec_label.setGeometry(QtCore.QRect(450, 210, 81, 31))
        font.setPointSize(14)
        self.deg_sec_label.setFont(font)
        self.Motor_dor_label.setGeometry(QtCore.QRect(540, 135, 191, 21))
        font.setPointSize(13)
        self.Motor_dor_label.setFont(font)
        self.Motor_dwell_label.setGeometry(QtCore.QRect(590, 192, 101, 21))
        self.line_horiz.setGeometry(QtCore.QRect(330, 120, 401, 20))
        self.Current_temp_label.setGeometry(QtCore.QRect(290, 0, 191, 41))
        font.setPointSize(22)
        self.Current_temp_label.setFont(font)
        self.Motor_speed_label.setGeometry(QtCore.QRect(290, 130, 101, 41))
        self.ct_c_label.setGeometry(QtCore.QRect(520, 40, 21, 31))
        self.st_c_label.setGeometry(QtCore.QRect(770, 50, 21, 31))
        self.dwell_sec_label.setGeometry(QtCore.QRect(670, 222, 41, 21))
        font.setPointSize(13)
        self.dwell_sec_label.setFont(font)
        self.dor_deg_label.setGeometry(QtCore.QRect(670, 165, 51, 21))
        font.setPointSize(13)
        self.dor_deg_label.setFont(font)
        self.line_horiz_graph.show()
        font.setBold(True)
        self.ST_SB.setGeometry(QtCore.QRect(550, 50, 221, 71))
        self.Set_temp_label.setGeometry(QtCore.QRect(580, 20, 161, 31))
        self.CT_SB.setGeometry(QtCore.QRect(270, 40, 251, 71))
        font.setPointSize(58)
        self.CT_SB.setFont(font)
        self.MS_SB.setGeometry(QtCore.QRect(270, 170, 181, 71))
        font.setPointSize(58)
        self.MS_SB.setFont(font)
        self.MDOR_SB.setGeometry(QtCore.QRect(570, 155, 101, 31))
        font.setPointSize(28)
        self.MDOR_SB.setFont(font)
        self.MD_SB.setGeometry(QtCore.QRect(560, 212, 111, 31))
        font.setPointSize(28)
        self.MD_SB.setFont(font)
        font.setPointSize(52)
        self.ST_SB.setFont(font)
        self.temp_graph.show()
    
    # Changes screen to hide graph
    def withoutGraph(self):
        font = QtGui.QFont()
        font.setFamily("Leelawadee UI")
        self.deg_sec_label.setGeometry(QtCore.QRect(460, 370, 101, 41))
        font.setPointSize(16)
        self.deg_sec_label.setFont(font)
        self.Motor_dor_label.setGeometry(QtCore.QRect(550, 230, 221, 31))
        font.setPointSize(14)
        self.Motor_dor_label.setFont(font)
        self.Motor_dwell_label.setGeometry(QtCore.QRect(600, 340, 111, 31))
        self.line_horiz.setGeometry(QtCore.QRect(360, 210, 351, 16))
        self.Current_temp_label.setGeometry(QtCore.QRect(280, 30, 211, 41))
        font.setPointSize(23)
        self.Current_temp_label.setFont(font)
        self.Motor_speed_label.setGeometry(QtCore.QRect(310, 260, 131, 51))
        self.ct_c_label.setGeometry(QtCore.QRect(550, 60, 16, 41))
        self.st_c_label.setGeometry(QtCore.QRect(760, 90, 21, 31))
        self.dwell_sec_label.setGeometry(QtCore.QRect(710, 410, 51, 31))
        font.setPointSize(16)
        self.dwell_sec_label.setFont(font)
        self.dor_deg_label.setGeometry(QtCore.QRect(710, 300, 81, 31))
        font.setPointSize(16)
        self.dor_deg_label.setFont(font)
        self.line_horiz_graph.hide()
        font.setBold(True)
        self.ST_SB.setGeometry(QtCore.QRect(570, 90, 191, 71))
        self.Set_temp_label.setGeometry(QtCore.QRect(590, 60, 161, 31))
        self.CT_SB.setGeometry(QtCore.QRect(270, 70, 281, 91))
        font.setPointSize(64)
        self.CT_SB.setFont(font)
        self.MS_SB.setGeometry(QtCore.QRect(280, 310, 181, 101))
        font.setPointSize(64)
        self.MS_SB.setFont(font)
        self.MDOR_SB.setGeometry(QtCore.QRect(540, 260, 171, 71))
        font.setPointSize(42)
        self.MDOR_SB.setFont(font)
        self.MD_SB.setGeometry(QtCore.QRect(570, 370, 141, 71))
        font.setPointSize(42)
        self.MD_SB.setFont(font)
        font.setPointSize(44)
        self.ST_SB.setFont(font)
        self.temp_graph.hide()

    # Rotates forward, determines if click or toggle is set in general settings
    def Forward(self):
        steps=int(round((motorSteps/6),0))
        if self.genwindow.Click_B.isChecked():
            log.debug("Rotate forward clicked")
            GPIO.output(DIR,CW)
            for x in range (steps):
                GPIO.output(STEP,GPIO.HIGH)
                time.sleep(.001)
                GPIO.output(STEP,GPIO.LOW)
                time.sleep(.001)
        else:
            if self.RotateFwd_B.isChecked():
                self.StartStopMotor_B.setEnabled(False)
                self.RotateRev_B.setEnabled(False)
                self.GenSettings_B.setEnabled(False)
                self.motorthread = QThread(parent=self)  # a new thread to run our background tasks in
                self.motorthread.daemon = True
                self.motorworker = MotorWorker()  # a new worker to perform those tasks
                self.motorworker.moveToThread(self.motorthread)  # move the worker into the thread, do this first before connecting the signals
                self.motorthread.started.connect(self.motorworker.work_fwd)  # begin our worker object's loop when the thread starts running
                self.motorthread.start()
            else:
                self.StartStopMotor_B.setEnabled(True)
                self.RotateRev_B.setEnabled(True)
                self.GenSettings_B.setEnabled(True)
                self.motorworker.fwd_working = False
                self.motorworker.finished.connect(self.motorthread.quit)  # tell the thread it's time to stop running
                self.motorworker.finished.connect(self.motorworker.deleteLater)  # have worker mark itself for deletion
                self.motorthread.finished.connect(self.motorthread.deleteLater)  # have thread mark itself for deletion

    # Rotates reverse, determines if click or toggle is set in general settings
    def Reverse(self):
        steps=int(round((motorSteps/6),0))
        if self.genwindow.Click_B.isChecked():
            log.debug("Rotate reverse clicked")
            GPIO.output(DIR,CCW)
            for x in range (steps):
                GPIO.output(STEP,GPIO.HIGH)
                time.sleep(.001)
                GPIO.output(STEP,GPIO.LOW)
                time.sleep(.001)
        else:
            if self.RotateRev_B.isChecked():
                self.StartStopMotor_B.setEnabled(False)
                self.RotateFwd_B.setEnabled(False)
                self.GenSettings_B.setEnabled(False)
                self.motorthread = QThread(parent=self)  # a new thread to run our background tasks in
                self.motorthread.daemon = True
                self.motorworker = MotorWorker()  # a new worker to perform those tasks
                self.motorworker.moveToThread(self.motorthread)  # move the worker into the thread, do this first before connecting the signals
                self.motorthread.started.connect(self.motorworker.work_rev)  # begin our worker object's loop when the thread starts running
                self.motorthread.start()
            else:
                self.StartStopMotor_B.setEnabled(True)
                self.RotateFwd_B.setEnabled(True)
                self.GenSettings_B.setEnabled(True)
                self.motorworker.rev_working = False
                self.motorworker.finished.connect(self.motorthread.quit)  # tell the thread it's time to stop running
                self.motorworker.finished.connect(self.motorworker.deleteLater)  # have worker mark itself for deletion
                self.motorthread.finished.connect(self.motorthread.deleteLater)  # have thread mark itself for deletion


    # Updates main screen from settings chosen in general settings window
    def updateGenSettings(self):
        if self.genwindow.Enable_on_B.isChecked():
            self.withGraph()
        else:
            self.withoutGraph()
        if self.genwindow.Toggle_B.isChecked():
            self.RotateFwd_B.setCheckable(True)
            self.RotateRev_B.setCheckable(True)
        else:
            self.RotateFwd_B.setCheckable(False)
            self.RotateRev_B.setCheckable(False)

    # Start/Stop Motor via Modbus write
    def modbusMotorChange(self):
        self.StartStopMotor_B.click()
    
    # "...click" functions show the settings windows
    def tempclick(self):
        log.debug("Opening Temperature Settings window")
        self.tempwindow.show()

    def motorclick(self):
        log.debug("Opening Motor Settings window")
        self.motorwindow.show()

    def genclick(self):
        log.debug("Opening General Settings window")
        self.genwindow.show()

    # Update functions used to update main screen when closing temperature settings or motor settings windows
    def updateST(self):
        self.ST_SB.setValue(self.tempwindow.setSpinBox.value())    #update set temp main window on save and close
        self.send_temp()

    def updateMS(self):
        self.MS_SB.setValue(self.motorwindow.msSpinBox.value())
        self.MDOR_SB.setValue(self.motorwindow.dorSpinBox.value())
        self.MD_SB.setValue(self.motorwindow.dwellSpinBox.value())

    def updateMB(self):
        log.debug("Updating ModBus values")
        self.serverworker.MB_set_temp = self.ST_SB.value()
        self.serverworker.MB_current_temp = self.CT_SB.value()
        self.serverworker.MB_motor_speed = self.MS_SB.value()
        self.serverworker.MB_motor_dor = self.MDOR_SB.value()
        self.serverworker.MB_motor_dwell = self.MD_SB.value()

    # Updates main screen if variables changed via Modbus writes
    def updateMainGUIValues(self):
        self.ST_SB.setValue(self.serverworker.MB_set_temp)
        self.MS_SB.setValue(self.serverworker.MB_motor_speed)
        self.MDOR_SB.setValue(self.serverworker.MB_motor_dor)
        self.MD_SB.setValue(self.serverworker.MB_motor_dwell)

    # Updates current temperature and graph when called via LoopingCall
    def updateGUICurrentTemp(self):
        self.CT_SB.setValue(self.serverworker.MB_current_temp)
        self.tempwindow.currentSpinBox.setValue(self.serverworker.MB_current_temp)
        self.updateGraph()
    
    # Updates alarm light and alarm info in general settings window
    # Sends alarm info to Modbus server by writing to discrete inputs
    def updateAlarms(self):
        self.alarm_info_str = "Alarms: "
        self.Alarm_List=[0,0,0,0,0,0,0]
        self.Alarm_List=self.serverworker.alarm_lst
        if self.Alarm_List[6] == 1:  #b[0]
            log.warning('High Alarm Detected')
            self.alarm_info_str += "High Temperature Alarm Detected!\n"
            self.serverworker.MB_alarm_hightemp = True
        else:
            self.serverworker.MB_alarm_hightemp = False
        if self.Alarm_List[5] == 1:  #b[1]
            log.warning('Low Alarm Detected')
            self.alarm_info_str += "Low Temperature Alarm Detected!\n"
            self.serverworker.MB_alarm_lowtemp = True
        else:
            self.serverworker.MB_alarm_lowtemp = False
        if self.Alarm_List[4] == 1:  #b[2]
            log.warning('Computer Controlled Alarm Detected')
            self.alarm_info_str += "Computer Controlled Alarm Detected!\n"
        if self.Alarm_List[3] == 1:  #b[3]
            log.warning('Over Current Detected')
            self.alarm_info_str += "Over Current Detected! TEC attempted to draw more current than allowed.\n"
            self.serverworker.MB_alarm_overcurrent = True
        else:
            self.serverworker.MB_alarm_overcurrent = False
        if self.Alarm_List[2] == 1:  #b[4]
            log.warning('Open Input 1 Detected')
            self.alarm_info_str += "OPEN INPUT1! There is a problem with the primary temperature sensor.\n"
            self.serverworker.MB_alarm_therm = True
        else:
            self.serverworker.MB_alarm_therm = False
        if self.Alarm_List[1] == 1:  #b[5]
            log.warning('Open Input 2 Detected')
            self.alarm_info_str += "OPEN INPUT2! There is a problem with the secondary temperature sensor.\n"       #should never trigger unless 2nd thermister
        if self.Alarm_List[0] == 1:  #b[3]
            log.warning('Driver Low Input Voltage Detected')
            self.alarm_info_str += "Driver Low Input Voltage Detected! The controller does not have a high enough voltage to properly operate.\n"
            self.serverworker.MB_alarm_low_voltage = True
        else:
            self.serverworker.MB_alarm_low_voltage = False
        if self.Alarm_List == [0,0,0,0,0,0,0]:
            self.alarm_bool=False
            palette = QtGui.QPalette()
            brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
            brush.setStyle(QtCore.Qt.SolidPattern)
            palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
            brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
            brush.setStyle(QtCore.Qt.SolidPattern)
            palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
            brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
            brush.setStyle(QtCore.Qt.SolidPattern)
            palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
            self.alarm_graphicsView.setPalette(palette)
            self.genwindow.Alarm_stat_graphicsView.setPalette(palette)
            self.genwindow.textBrowser.setText("")
        else:
            self.alarm_bool=True
            palette = QtGui.QPalette()
            brush = QtGui.QBrush(QtGui.QColor(255, 0, 0))
            brush.setStyle(QtCore.Qt.SolidPattern)
            palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
            brush = QtGui.QBrush(QtGui.QColor(255, 0, 0))
            brush.setStyle(QtCore.Qt.SolidPattern)
            palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
            brush = QtGui.QBrush(QtGui.QColor(43, 43, 43))
            brush.setStyle(QtCore.Qt.SolidPattern)
            palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
            self.alarm_graphicsView.setPalette(palette)
            self.genwindow.Alarm_stat_graphicsView.setPalette(palette)
            self.genwindow.textBrowser.setText(self.alarm_info_str)

    # Updates set temp on main screen via writes to Modbus server
    def send_temp_fromMB(self):
        self.ST_SB.setValue(self.serverworker.MB_set_temp)
        self.send_temp()

    # Sets initial set temp on main screen by checking saved set temp on temp controller
    def initialSetTemp(self):
        self.ST_SB.setValue(self.serverworker.initSetTemp)
        self.tempwindow.setSpinBox.setValue(self.serverworker.initSetTemp)

    # Handler for Start/Stop button press
    def StartStopHandler(self):
        if self.StartStopMotor_B.isChecked():
            self.motorthread = QThread(parent=self)  # a new thread to run our background tasks in
            self.motorthread.daemon = True
            self.motorworker = MotorWorker()  # a new worker to perform those tasks
            self.motorworker.moveToThread(self.motorthread)  # move the worker into the thread, do this first before connecting the signals
            self.motorthread.started.connect(self.motorworker.work)  # begin our worker object's loop when the thread starts running
            self.motorthread.start()
            self.motorworker.speed = self.MS_SB.value()
            self.motorworker.dor = self.MDOR_SB.value()
            self.motorworker.dwell = self.MD_SB.value()
            self.serverworker.MB_motor_on = True
            self.serverworker.GUI_motorFlag = True
        else:
            self.serverworker.MB_motor_on = False
            self.serverworker.GUI_motorFlag = True
            self.motorworker.working = False
            #self.motorworker.finished.connect(self.loop_finished)  # do something in the gui when the worker loop ends
            self.motorworker.finished.connect(self.motorthread.quit)  # tell the thread it's time to stop running
            self.motorworker.finished.connect(self.motorworker.deleteLater)  # have worker mark itself for deletion
            self.motorthread.finished.connect(self.motorthread.deleteLater)  # have thread mark itself for deletion
            # make sure those last two are connected to themselves or you will get random crashes

    # Creates modbus server in seperate thread via ServerWorker class
    def StartServer(self):
        log.info("Starting ModBus Server...")
        self.serverthread = QThread(parent=self)  # a new thread to run our background tasks in
        self.serverworker = ServerWorker()  # a new worker to perform those tasks
        self.serverworker.moveToThread(self.serverthread)  # move the worker into the thread, do this first before connecting the signals
        self.serverthread.started.connect(self.serverworker.work)  # begin our worker object's loop when the thread starts running
        self.serverthread.start()
        self.serverworker.MB_set_temp = self.ST_SB.value()
        self.serverworker.MB_current_temp = self.CT_SB.value()
        self.serverworker.MB_motor_speed = self.MS_SB.value()
        self.serverworker.MB_motor_dor = self.MDOR_SB.value()
        self.serverworker.MB_motor_dwell = self.MD_SB.value()

    # Sends set temp to temp controller
    def send_temp(self):
        buf=['*','0','0','0','0','0','0','0','0','0','0','^']
        A1, A2='0','2'
        C1,C2='1','c'
        set_temp=float(self.ST_SB.value())
        desired_temp = set_temp * 100
        desired_temp = int(round(desired_temp))
        if desired_temp < 0:
            desired_temp = (0xffffffff - (-desired_temp)) + 1
        desired_temp=hex(desired_temp)[2:]
        desired_temp=list(desired_temp)
        while len(desired_temp) < 8:
            desired_temp.insert(0,'0')
        D1,D2,D3,D4,D5,D6,D7,D8=desired_temp
        S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
        bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
        for pn in range(0,16):
            ser.write(bst[pn].encode())
        for pn in range(0,12):
            buf[pn]=ser.read(1)
    
    # Updates graph with current temp reading (y-axis) and time since start (x-axis)
    def updateGraph(self):
        self.x=self.x[1:]
        self.x.append(round(time.time(),2)-self.initTime)
        self.y=self.y[1:]
        self.y.append(self.CT_SB.value())
        self.data.setData(self.x, self.y)
    

if __name__ == "__main__":
    app = QApplication(sys.argv)    # config for OS
    win = MyWindow()                # creates main window

    win.show()                      # show main window

    sys.exit(app.exec())
