from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal,  QTimer
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

global TempCurrent
global TempSet 
global MotorSpeed
global MotorDwell
global MotorAngle

def updating_writer(a):
    """ A worker process that runs every so often and
    updates live values of the context. It should be noted
    that there is a race condition for the update.

    :param arguments: The input arguments to the call
    """
    log.debug("updating the context")
    context = a[0]
    register = 3
    slave_id = 0x00
    address = 0x10
    values = context[slave_id].getValues(register, address, count=5)
    values = [v + 1 for v in values]
    log.debug("new values: " + str(values))
    context[slave_id].setValues(register, address, values)

class ServerWorker(QThread):

    def __init__(self):
        super(ServerWorker, self).__init__()
        self.working = True
        

    def work(self):
        print("init server")
        print(self.currentThread())
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
        time = 5  # 5 seconds delay
        loop = LoopingCall(f=updating_writer, a=(context,))
        loop.start(time, now=False) # initially delay by time
        
        sleep(0.1)
        StartTcpServer(context, identity=identity, address=("localhost", 5020))




class MotorWorker(QThread):
    finished = pyqtSignal()  # our signal out to the main thread to alert it we've completed our work

    def __init__(self):
        super(MotorWorker, self).__init__()
        self.working = True  # this is our flag to control our loop

    def work(self):
        while self.working:
            print ("Hello!")
            print(self.currentThread())
            sleep(1)

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

class TempWindow(QMainWindow):

    def __init__(self):
        super(TempWindow, self).__init__()
        self.setGeometry(200, 200, 800, 450)
        self.initUI()

    def initUI(self):
        self.setObjectName("Temperature Settings")
        self.resize(800, 450)
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
        self.SaveAndClose = QtWidgets.QPushButton(self.centralwidget)
        self.SaveAndClose.setGeometry(QtCore.QRect(10, 10, 421, 131))
        self.SaveAndClose.setObjectName("SaveAndClose")
        self.DesiredTemp = QtWidgets.QLabel(self.centralwidget)
        self.DesiredTemp.setGeometry(QtCore.QRect(490, 50, 131, 51))
        self.DesiredTemp.setObjectName("DesiredTemp")
        self.setCentralWidget(self.centralwidget)

        self.retranslateUi(self)
        QtCore.QMetaObject.connectSlotsByName(self)

        self.SaveAndClose.clicked.connect(self.SaC)

    def SaC(self):
        self.close()
    
    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("Temperature Settings", "Temperature Settings"))
        self.plus10.setText(_translate("Temperature Settings", "+ 10"))
        self.plus1.setText(_translate("Temperature Settings", "+ 1"))
        self.plus01.setText(_translate("Temperature Settings", "+ 0.1"))
        self.minus10.setText(_translate("Temperature Settings", "- 10"))
        self.minus1.setText(_translate("Temperature Settings", "- 1"))
        self.minus01.setText(_translate("Temperature Settings", "- 0.1"))
        self.SaveAndClose.setText(_translate("Temperature Settings", "Save and Close"))
        self.DesiredTemp.setText(_translate("Temperature Settings", "Desired Temperature: "))

class MyWindow(QMainWindow):        #can name MyWindow anything, inherit QMainWindow class

    def __init__(self):
        super(MyWindow, self).__init__()        #super refrences top lvl class
        self.setGeometry(200, 200, 800, 450)
        self.initUI()

    def initUI(self):
        self.setObjectName("MainWindow")
        self.resize(800, 450)
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
        self.setCentralWidget(self.centralwidget)

        self.retranslateUi(self)
        QtCore.QMetaObject.connectSlotsByName(self)

        self.StartServer()

        self.tempwindow = TempWindow()
        self.TempSettings.clicked.connect(self.tempclick)

        self.StartStopMotor.clicked.connect(self.StartStopHandler)


    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.StartStopMotor.setText(_translate("MainWindow", "Start / Stop Motor"))
        self.MotorSettings.setText(_translate("MainWindow", "Motor Settings"))
        self.RotateFwd.setText(_translate("MainWindow", "Rotate Fwd"))
        self.RotateRev.setText(_translate("MainWindow", "Rotate Rev"))
        self.TempSettings.setText(_translate("MainWindow", "Temp Settings"))

    def tempclick(self):
        #MyWindow.hide(self)         #or self.hide()
        self.tempwindow.show()

    def StartStopHandler(self):
        if self.StartStopMotor.isChecked():
            self.motorthread = QThread(parent=self)  # a new thread to run our background tasks in
            self.motorthread.daemon = True
            self.motorworker = MotorWorker()  # a new worker to perform those tasks
            self.motorworker.moveToThread(self.motorthread)  # move the worker into the thread, do this first before connecting the signals

            self.motorthread.started.connect(self.motorworker.work)  # begin our worker object's loop when the thread starts running
            self.motorthread.start()
            #self.StartStopMotor.clicked.connect(self.stop_loop)  # stop the loop on the stop button click [DELETE line]
        else:
            self.motorworker.working = False
            self.motorworker.finished.connect(self.loop_finished)  # do something in the gui when the worker loop ends
            self.motorworker.finished.connect(self.motorthread.quit)  # tell the thread it's time to stop running
            self.motorworker.finished.connect(self.motorworker.deleteLater)  # have worker mark itself for deletion
            self.motorthread.finished.connect(self.motorthread.deleteLater)  # have thread mark itself for deletion
            # make sure those last two are connected to themselves or you will get random crashes

    def StartServer(self):
        print("start server")
        self.serverthread = QThread(parent=self)  # a new thread to run our background tasks in
        self.serverworker = ServerWorker()  # a new worker to perform those tasks
        self.serverworker.moveToThread(self.serverthread)  # move the worker into the thread, do this first before connecting the signals

        self.serverthread.started.connect(self.serverworker.work)  # begin our worker object's loop when the thread starts running
        self.serverthread.start()
            
    def loop_finished(self):
        # received a callback from the thread that it completed
        print('Looped Finished')



if __name__ == "__main__":
    app = QApplication(sys.argv)    #config for OS
    win = MyWindow()

    win.show()

    sys.exit(app.exec())
