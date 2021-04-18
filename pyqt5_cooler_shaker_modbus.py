# Written by: Alexander Lopez
# Date Last Modified: 3/28/21

# ------ ABOUT -------
# This code is a work in progress. The purpose is to create a GUI that operates the liquid sampple cooler-shaker system and connects to a Modbus TCP client

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow

from pymodbus.version import version
from pymodbus.server.asynchronous import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer, ModbusAsciiFramer

from twisted.internet.task import LoopingCall

#import RPi.GPIO as GPIO
from time import sleep

import sys

import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

#global TempCurrent
#global TempSet 
#global MotorSpeed
#global MotorDwell
#global MotorAngle

motorSteps = 200

class ServerWorker(QThread):

    updateModbusValues = pyqtSignal()

    def __init__(self):
        super(ServerWorker, self).__init__()
        self.MB_goal_temp = 0.0
        self.MB_current_temp = 0.0
        self.MB_motor_speed = 0
        self.MB_motor_dor = 0
        self.MB_motor_dwell = 0

    def work(self):
        log.info(self.currentThread())
        sleep(0.1)
        store = ModbusSlaveContext(
            di=ModbusSequentialDataBlock(0, [17]*100),
            co=ModbusSequentialDataBlock(0, [17]*100),
            hr=ModbusSequentialDataBlock(0, [17]*100),
            ir=ModbusSequentialDataBlock(0, [17]*100))
        context = ModbusServerContext(slaves=store, single=True)
        # ----------------------------------------------------------------------- # 
        # initialize the server information
        # ----------------------------------------------------------------------- # 
        identity = ModbusDeviceIdentification()
        identity.VendorName = 'pymodbus'
        identity.ProductCode = 'PM'
        identity.VendorUrl = 'http://github.com/riptideio/pymodbus/'
        identity.ProductName = 'pymodbus Server'
        identity.ModelName = 'pymodbus Server'
        identity.MajorMinorRevision = version.short()
        time = 4.9  # 5 seconds delay
        loop = LoopingCall(f=self.updating_writer, a=(context,))
        loop.start(time, now=False) # initially delay by time
        
        sleep(0.1)
        StartTcpServer(context, identity=identity, address=("localhost", 5020))

    def updating_writer(self, a):
        """ A worker process that runs every so often and
        updates live values of the context. It should be noted
        that there is a race condition for the update.

        :param arguments: The input arguments to the call
        """
        log.debug("updating the context")
        self.updateModbusValues.emit()
        sleep(0.1)

        print(self.MB_goal_temp)
        print(self.MB_current_temp)
        print(self.MB_motor_speed)
        print(self.MB_motor_dor)
        print(self.MB_motor_dwell)

        context = a[0]
        print(context)
        register = 3
        slave_id = 0x00
        address = 0x10
        values = context[slave_id].getValues(register, address, count=5)
        print(values)
        values = [v + 1 for v in values]
        log.debug("new values: " + str(values))
        context[slave_id].setValues(register, address, values)


class MotorWorker(QThread):
    finished = pyqtSignal()  # our signal out to the main thread to alert it we've completed our work

    def __init__(self):
        super(MotorWorker, self).__init__()
        self.working = True  # this is our flag to control our loop

    def work(self):
        while self.working:
            print ("Motor Running!")
            print(self.currentThread())
            sleep(3)

            """ 
            sleep(dwell)
            #GPIO.output(DIR,CW)
            i = 0
            for x in range(round(angle/1.8)):
                print ('CW'+str(i))
                #GPIO.output(STEP,GPIO.HIGH)
                sleep(((1.8)/(2*(rotation))))
                #GPIO.output(STEP,GPIO.LOW)
                sleep(((1.8)/(2*(rotation))))
                i +=1
        
            sleep(dwell)
            #GPIO.output(DIR,CCW)
            i = 0
            for x in rannge(round(angle/1.8)):
                print ('CCW'+str(i))
                #GPIO.output(STEP,GPIO.HIGH)
                sleep(((1.8)/(2*(rotation))))
                #GPIO.output(STEP,GPIO.LOW)
                sleep(((1.8)/(2*(rotation))))
                i +=1
            """
        self.finished.emit() # alert our gui that the loop stopped

class MotorWindow(QMainWindow):

    saveMotorSettings = pyqtSignal()

    def __init__(self):
        super(MotorWindow, self).__init__()
        self.setGeometry(0, 0, 800, 480)
        self.initUI()

    def initUI(self):
        self.setObjectName("Motor Settings")
        self.resize(800, 480)
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.SaveAndCloseMotor = QtWidgets.QPushButton(self.centralwidget)
        self.SaveAndCloseMotor.setGeometry(QtCore.QRect(10, 10, 421, 131))
        self.SaveAndCloseMotor.setObjectName("SaveAndCloseMotor")
        self.msSpinBox = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.msSpinBox.setGeometry(QtCore.QRect(170, 160, 41, 31))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.msSpinBox.setFont(font)
        self.msSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.msSpinBox.setDecimals(0)
        self.msSpinBox.setMaximum(360.0)
        self.msSpinBox.setSingleStep(15.0)
        self.msSpinBox.setProperty("value", 90.0)
        self.msSpinBox.setObjectName("msSpinBox")
        self.dorSpinBox = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.dorSpinBox.setGeometry(QtCore.QRect(470, 160, 41, 31))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.dorSpinBox.setFont(font)
        self.dorSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.dorSpinBox.setDecimals(0)
        self.dorSpinBox.setMaximum(360.0)
        self.dorSpinBox.setSingleStep(45.0)
        self.dorSpinBox.setProperty("value", 360.0)
        self.dorSpinBox.setObjectName("dorSpinBox")
        self.dwellSpinBox = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.dwellSpinBox.setGeometry(QtCore.QRect(670, 160, 41, 31))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.dwellSpinBox.setFont(font)
        self.dwellSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.dwellSpinBox.setDecimals(1)
        self.dwellSpinBox.setMaximum(10.0)
        self.dwellSpinBox.setSingleStep(0.5)
        self.dwellSpinBox.setProperty("value", 0.5)
        self.dwellSpinBox.setObjectName("dwellSpinBox")
        self.SpeedLabel = QtWidgets.QLabel(self.centralwidget)
        self.SpeedLabel.setGeometry(QtCore.QRect(10, 150, 151, 41))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.SpeedLabel.setFont(font)
        self.SpeedLabel.setObjectName("SpeedLabel")
        self.DORLabel = QtWidgets.QLabel(self.centralwidget)
        self.DORLabel.setGeometry(QtCore.QRect(290, 150, 171, 41))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.DORLabel.setFont(font)
        self.DORLabel.setObjectName("DORLabel")
        self.DwellLabel = QtWidgets.QLabel(self.centralwidget)
        self.DwellLabel.setGeometry(QtCore.QRect(570, 150, 101, 41))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.DwellLabel.setFont(font)
        self.DwellLabel.setObjectName("DwellLabel")
        self.PlusSpeed = QtWidgets.QPushButton(self.centralwidget)
        self.PlusSpeed.setGeometry(QtCore.QRect(10, 200, 250, 125))
        font = QtGui.QFont()
        font.setPointSize(28)
        self.PlusSpeed.setFont(font)
        self.PlusSpeed.setObjectName("PlusSpeed")
        self.PlusDOR = QtWidgets.QPushButton(self.centralwidget)
        self.PlusDOR.setGeometry(QtCore.QRect(270, 200, 250, 125))
        font = QtGui.QFont()
        font.setPointSize(28)
        self.PlusDOR.setFont(font)
        self.PlusDOR.setObjectName("PlusDOR")
        self.PlusDwell = QtWidgets.QPushButton(self.centralwidget)
        self.PlusDwell.setGeometry(QtCore.QRect(530, 200, 250, 125))
        font = QtGui.QFont()
        font.setPointSize(28)
        self.PlusDwell.setFont(font)
        self.PlusDwell.setObjectName("PlusDwell")
        self.MinusSpeed = QtWidgets.QPushButton(self.centralwidget)
        self.MinusSpeed.setGeometry(QtCore.QRect(10, 340, 250, 125))
        font = QtGui.QFont()
        font.setPointSize(28)
        self.MinusSpeed.setFont(font)
        self.MinusSpeed.setObjectName("MinusSpeed")
        self.MinusDOR = QtWidgets.QPushButton(self.centralwidget)
        self.MinusDOR.setGeometry(QtCore.QRect(270, 340, 250, 125))
        font = QtGui.QFont()
        font.setPointSize(28)
        self.MinusDOR.setFont(font)
        self.MinusDOR.setObjectName("MinusDOR")
        self.MinusDwell = QtWidgets.QPushButton(self.centralwidget)
        self.MinusDwell.setGeometry(QtCore.QRect(530, 340, 250, 125))
        font = QtGui.QFont()
        font.setPointSize(28)
        self.MinusDwell.setFont(font)
        self.MinusDwell.setObjectName("MinusDwell")
        self.setCentralWidget(self.centralwidget)

        self.retranslateUi(self)
        QtCore.QMetaObject.connectSlotsByName(self)

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
        self.SaveAndCloseMotor.setText(_translate("Motor Settings", "Save and Close"))
        self.SpeedLabel.setText(_translate("Motor Settings", "Motor Speed (deg/sec)"))
        self.DORLabel.setText(_translate("Motor Settings", "Degrees of Rotation (deg)"))
        self.DwellLabel.setText(_translate("Motor Settings", "Dwell Time (s)"))
        self.PlusSpeed.setText(_translate("Motor Settings", "+"))
        self.PlusDOR.setText(_translate("Motor Settings", "+"))
        self.PlusDwell.setText(_translate("Motor Settings", "+"))
        self.MinusSpeed.setText(_translate("Motor Settings", "-"))
        self.MinusDOR.setText(_translate("Motor Settings", "-"))
        self.MinusDwell.setText(_translate("Motor Settings", "-"))

    def SaCM(self):
        self.saveMotorSettings.emit()
        self.hide()

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

class TempWindow(QMainWindow):

    saveTempSettings = pyqtSignal()

    def __init__(self):
        super(TempWindow, self).__init__()
        self.setGeometry(0, 0, 800, 480)
        self.initUI()

    def initUI(self):
        self.setObjectName("Temperature Settings")
        self.resize(800, 480)
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.plus10 = QtWidgets.QPushButton(self.centralwidget)
        self.plus10.setGeometry(QtCore.QRect(10, 150, 250, 125))
        self.plus10.setObjectName("plus10")
        self.plus1 = QtWidgets.QPushButton(self.centralwidget)
        self.plus1.setGeometry(QtCore.QRect(270, 150, 250, 125))
        self.plus1.setObjectName("plus1")
        self.plus01 = QtWidgets.QPushButton(self.centralwidget)
        self.plus01.setGeometry(QtCore.QRect(530, 150, 250, 125))
        self.plus01.setObjectName("plus01")
        self.minus10 = QtWidgets.QPushButton(self.centralwidget)
        self.minus10.setGeometry(QtCore.QRect(10, 290, 250, 125))
        self.minus10.setObjectName("minus10")
        self.minus1 = QtWidgets.QPushButton(self.centralwidget)
        self.minus1.setGeometry(QtCore.QRect(270, 290, 250, 125))
        self.minus1.setObjectName("minus1")
        self.minus01 = QtWidgets.QPushButton(self.centralwidget)
        self.minus01.setGeometry(QtCore.QRect(530, 290, 250, 125))
        self.minus01.setObjectName("minus01")
        self.SaveAndCloseTemp = QtWidgets.QPushButton(self.centralwidget)
        self.SaveAndCloseTemp.setGeometry(QtCore.QRect(10, 10, 420, 130))
        self.SaveAndCloseTemp.setObjectName("SaveAndCloseTemp")

        self.goalTempLabel = QtWidgets.QLabel(self.centralwidget)
        self.goalTempLabel.setGeometry(QtCore.QRect(490, 50, 130, 50))
        self.goalTempLabel.setObjectName("goalTempLabel")

        self.goalSpinBox = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.goalSpinBox.setGeometry(QtCore.QRect(590, 60, 50, 30))
        self.goalSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.goalSpinBox.setDecimals(1)
        #self.goalSpinBox.setSingleStep(1.0)
        self.goalSpinBox.setObjectName("goalSpinBox")

        self.setCentralWidget(self.centralwidget)

        self.retranslateUi(self)
        QtCore.QMetaObject.connectSlotsByName(self)

        self.plus10.clicked.connect(self.p10)
        self.plus1.clicked.connect(self.p1)
        self.plus01.clicked.connect(self.p01)
        self.minus10.clicked.connect(self.m10)
        self.minus1.clicked.connect(self.m1)
        self.minus01.clicked.connect(self.m01)

        self.SaveAndCloseTemp.clicked.connect(self.SaCT)
    
    def retranslateUi(self, TempWindow):
        _translate = QtCore.QCoreApplication.translate
        TempWindow.setWindowTitle(_translate("Temperature Settings", "Temperature Settings"))
        self.plus10.setText(_translate("Temperature Settings", "+ 10"))
        self.plus1.setText(_translate("Temperature Settings", "+ 1"))
        self.plus01.setText(_translate("Temperature Settings", "+ 0.1"))
        self.minus10.setText(_translate("Temperature Settings", "- 10"))
        self.minus1.setText(_translate("Temperature Settings", "- 1"))
        self.minus01.setText(_translate("Temperature Settings", "- 0.1"))
        self.SaveAndCloseTemp.setText(_translate("Temperature Settings", "Save and Close"))
        self.goalTempLabel.setText(_translate("Temperature Settings", "Goal Temperature: "))

    def SaCT(self):                 # hide window and update main window
        self.saveTempSettings.emit()
        self.hide()

    def p10(self):
        self.goalSpinBox.setSingleStep(10.0)
        self.goalSpinBox.stepUp()

    def p1(self):
        self.goalSpinBox.setSingleStep(1.0)
        self.goalSpinBox.stepUp()
    
    def p01(self):
        self.goalSpinBox.setSingleStep(0.1)
        self.goalSpinBox.stepUp()
    
    def m10(self):
        self.goalSpinBox.setSingleStep(10.0)
        self.goalSpinBox.stepDown()

    def m1(self):
        self.goalSpinBox.setSingleStep(1.0)
        self.goalSpinBox.stepDown()
    
    def m01(self):
        self.goalSpinBox.setSingleStep(0.1)
        self.goalSpinBox.stepDown()

class MyWindow(QMainWindow):        #can name MyWindow anything, inherit QMainWindow class

    def __init__(self):
        super(MyWindow, self).__init__()        #super refrences top lvl class
        self.setGeometry(0, 0, 800, 480)
        self.initUI()

    def initUI(self):
        self.setObjectName("MainWindow")
        self.resize(800, 480)
        self.setTabShape(QtWidgets.QTabWidget.Rounded)
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.StartStopMotor = QtWidgets.QPushButton(self.centralwidget)
        self.StartStopMotor.setGeometry(QtCore.QRect(0, 0, 200, 80))
        self.StartStopMotor.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.StartStopMotor.setCheckable(True)
        self.StartStopMotor.setObjectName("StartStopMotor")
        self.MotorSettings = QtWidgets.QPushButton(self.centralwidget)
        self.MotorSettings.setGeometry(QtCore.QRect(0, 90, 200, 80))
        self.MotorSettings.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.MotorSettings.setAutoFillBackground(False)
        self.MotorSettings.setObjectName("MotorSettings")
        self.RotateFwd = QtWidgets.QPushButton(self.centralwidget)
        self.RotateFwd.setGeometry(QtCore.QRect(0, 270, 200, 80))
        self.RotateFwd.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.RotateFwd.setObjectName("RotateFwd")
        self.RotateRev = QtWidgets.QPushButton(self.centralwidget)
        self.RotateRev.setGeometry(QtCore.QRect(0, 180, 200, 80))
        self.RotateRev.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.RotateRev.setObjectName("RotateRev")
        self.TempSettings = QtWidgets.QPushButton(self.centralwidget)
        self.TempSettings.setGeometry(QtCore.QRect(600, 0, 200, 80))
        self.TempSettings.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.TempSettings.setObjectName("TempSettings")
        self.GT_SB = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.GT_SB.setGeometry(QtCore.QRect(320, 30, 51, 31))
        self.GT_SB.setInputMethodHints(QtCore.Qt.ImhFormattedNumbersOnly)
        self.GT_SB.setReadOnly(False)
        self.GT_SB.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.GT_SB.setDecimals(1)
        self.GT_SB.setSingleStep(1.0)
        self.GT_SB.setObjectName("GT_SB")
        self.Goal_temp_label = QtWidgets.QLabel(self.centralwidget)
        self.Goal_temp_label.setGeometry(QtCore.QRect(230, 20, 91, 51))
        self.Goal_temp_label.setObjectName("Goal_temp_label")
        self.Current_temp_label = QtWidgets.QLabel(self.centralwidget)
        self.Current_temp_label.setGeometry(QtCore.QRect(210, 70, 101, 51))
        self.Current_temp_label.setObjectName("Current_temp_label")
        self.CT_SB = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.CT_SB.setGeometry(QtCore.QRect(320, 80, 51, 31))
        self.CT_SB.setInputMethodHints(QtCore.Qt.ImhFormattedNumbersOnly)
        self.CT_SB.setReadOnly(False)
        self.CT_SB.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.CT_SB.setDecimals(1)
        self.CT_SB.setSingleStep(0.01)
        self.CT_SB.setObjectName("CT_SB")
        self.Motor_speed_label = QtWidgets.QLabel(self.centralwidget)
        self.Motor_speed_label.setGeometry(QtCore.QRect(430, 30, 111, 31))
        self.Motor_speed_label.setObjectName("Motor_speed_label")
        self.Motor_dor_label = QtWidgets.QLabel(self.centralwidget)
        self.Motor_dor_label.setGeometry(QtCore.QRect(380, 80, 161, 31))
        self.Motor_dor_label.setObjectName("Motor_dor_label")
        self.Motor_dwell_label = QtWidgets.QLabel(self.centralwidget)
        self.Motor_dwell_label.setGeometry(QtCore.QRect(430, 130, 101, 31))
        self.Motor_dwell_label.setObjectName("Motor_dwell_label")
        self.MS_SB = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.MS_SB.setGeometry(QtCore.QRect(540, 30, 51, 31))
        self.MS_SB.setInputMethodHints(QtCore.Qt.ImhFormattedNumbersOnly)
        self.MS_SB.setReadOnly(False)
        self.MS_SB.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.MS_SB.setDecimals(0)
        self.MS_SB.setMaximum(360.0)
        self.MS_SB.setSingleStep(1.0)
        self.MS_SB.setProperty("value", 90.0)
        self.MS_SB.setObjectName("MS_SB")
        self.MDOR_SB = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.MDOR_SB.setGeometry(QtCore.QRect(540, 80, 51, 31))
        self.MDOR_SB.setInputMethodHints(QtCore.Qt.ImhFormattedNumbersOnly)
        self.MDOR_SB.setReadOnly(False)
        self.MDOR_SB.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.MDOR_SB.setDecimals(0)
        self.MDOR_SB.setMaximum(360.0)
        self.MDOR_SB.setSingleStep(15.0)
        self.MDOR_SB.setProperty("value", 360.0)
        self.MDOR_SB.setObjectName("MDOR_SB")
        self.MD_SB = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.MD_SB.setGeometry(QtCore.QRect(540, 130, 51, 31))
        self.MD_SB.setInputMethodHints(QtCore.Qt.ImhFormattedNumbersOnly)
        self.MD_SB.setReadOnly(False)
        self.MD_SB.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.MD_SB.setDecimals(1)
        self.MD_SB.setMaximum(10.0)
        self.MD_SB.setSingleStep(0.5)
        self.MD_SB.setProperty("value", 0.5)
        self.MD_SB.setObjectName("MD_SB")

        self.setCentralWidget(self.centralwidget)

        self.retranslateUi(self)
        QtCore.QMetaObject.connectSlotsByName(self)

        self.StartServer()

        self.tempwindow = TempWindow()
        self.motorwindow = MotorWindow()
        self.TempSettings.clicked.connect(self.tempclick)
        self.MotorSettings.clicked.connect(self.motorclick)

        #self.tempwindow.goalSpinBox.valueChanged['double'].connect(self.GT_SB.setValue)     # passes data from tempwindow to the main screen
        # does this as number is changed, replaced with saveTempSettings signal

        self.tempwindow.saveTempSettings.connect(self.updateGT)     # on save aand close, updates main window
        self.motorwindow.saveMotorSettings.connect(self.updateMS)
        self.serverworker.updateModbusValues.connect(self.updateMB)

        self.StartStopMotor.clicked.connect(self.StartStopHandler)


    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.StartStopMotor.setText(_translate("MainWindow", "Start / Stop Motor"))
        self.MotorSettings.setText(_translate("MainWindow", "Motor Settings"))
        self.RotateFwd.setText(_translate("MainWindow", "Rotate Fwd"))
        self.RotateRev.setText(_translate("MainWindow", "Rotate Rev"))
        self.TempSettings.setText(_translate("MainWindow", "Temp Settings"))
        self.Goal_temp_label.setText(_translate("MainWindow", "Goal Temperature"))
        self.Current_temp_label.setText(_translate("MainWindow", "Current Temperature"))
        self.Motor_speed_label.setText(_translate("MainWindow", "Motor Speed (deg/sec)"))
        self.Motor_dor_label.setText(_translate("MainWindow", "Motor Degrees of rotation (deg)"))
        self.Motor_dwell_label.setText(_translate("MainWindow", "Motor Dwell Time (s)"))

    def tempclick(self):
        self.tempwindow.show()

    def motorclick(self):
        self.motorwindow.show()

    def updateGT(self):
        self.GT_SB.setValue(self.tempwindow.goalSpinBox.value())    #update goal temp main window on save and close

    def updateMS(self):
        self.MS_SB.setValue(self.motorwindow.msSpinBox.value())
        self.MDOR_SB.setValue(self.motorwindow.dorSpinBox.value())
        self.MD_SB.setValue(self.motorwindow.dwellSpinBox.value())

    def updateMB(self):
        self.serverworker.MB_goal_temp = self.GT_SB.value()
        self.serverworker.MB_current_temp = self.CT_SB.value()
        self.serverworker.MB_motor_speed = self.MS_SB.value()
        self.serverworker.MB_motor_dor = self.MDOR_SB.value()
        self.serverworker.MB_motor_dwell = self.MD_SB.value()

    def StartStopHandler(self):
        if self.StartStopMotor.isChecked():
            self.motorthread = QThread(parent=self)  # a new thread to run our background tasks in
            self.motorthread.daemon = True
            self.motorworker = MotorWorker()  # a new worker to perform those tasks
            self.motorworker.moveToThread(self.motorthread)  # move the worker into the thread, do this first before connecting the signals

            self.motorthread.started.connect(self.motorworker.work)  # begin our worker object's loop when the thread starts running
            self.motorthread.start()
        else:
            self.motorworker.working = False
            self.motorworker.finished.connect(self.loop_finished)  # do something in the gui when the worker loop ends
            self.motorworker.finished.connect(self.motorthread.quit)  # tell the thread it's time to stop running
            self.motorworker.finished.connect(self.motorworker.deleteLater)  # have worker mark itself for deletion
            self.motorthread.finished.connect(self.motorthread.deleteLater)  # have thread mark itself for deletion
            # make sure those last two are connected to themselves or you will get random crashes

    def StartServer(self):
        print("Starting server...")
        self.serverthread = QThread(parent=self)  # a new thread to run our background tasks in
        self.serverworker = ServerWorker()  # a new worker to perform those tasks
        self.serverworker.moveToThread(self.serverthread)  # move the worker into the thread, do this first before connecting the signals

        self.serverthread.started.connect(self.serverworker.work)  # begin our worker object's loop when the thread starts running
        self.serverthread.start()
            
    def loop_finished(self):
        # received a callback from the thread that it completed
        print('Loop Finished')



if __name__ == "__main__":
    app = QApplication(sys.argv)    #config for OS
    win = MyWindow()

    win.show()

    sys.exit(app.exec())
