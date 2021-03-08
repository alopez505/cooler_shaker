## import tkinter GUI python script decoder
import tkinter as tk
from tkinter import *
##import tkinter.font in order to change font sizes inside GUI
import tkinter.font as font
##impor sys for ability to control GPIO ouputs
import sys
## import the sleep functions for the motor controls to control motor speed and dwell times
from time import sleep
##import RPi.GPIO to unlock the raspberry pi gpio ports
import RPi.GPIO as gpio
##import numpy to allow for floating point conversions for the delay value calculations for precise speed control
import numpy as np
##import decimal for addition of small increment values to variables
from decimal import Decimal
root = tk.Tk()

## Set global variables so that they can be manipulated in both screens and they can transfer information seamlessly
global temp
global rotation
global angle
global dwell
global runtime

## Set initial values for variables
##set temp to decimal so that  values like .1 and .01 can be added to it
##Default temperature value stored here
temp = Decimal('4.00')

## set default  values for the motor controls
rotation = 90
angle =360
dwell=1

## set runtime to false so that motor doesnt start turning on power up
runtime = False

## set GPIO pins for motor controls
DIR = 20
STEP = 21

## definne values for clockwise and counter clockwise directions
CW = 1
CCW = 0

##Gpio set up for which port is direction and step for stepper motor controls
gpio.setmode(gpio.BCM)
gpio.setup(DIR, gpio.OUT)
gpio.setup(STEP, gpio.OUT)
            

## Home page class taht defines the buttons on the first page
class Demo1:
    def __init__(self, master):
        
        
        ## define variables so they can be manipulated inside this class and transferred from outside class
        global temp
        global rotation
        global angle
        global dwell
        global runtime
        
        ## set font sizes of buttons (myfont) and fo the labels (labelFont)
        myFont = font.Font(size=25)
        labelFont = font.Font(size=15)
        
        ##make this page same as master onfiguration as well as set the background color of this page
        self.master = master
        self.frame = tk.Frame(self.master, bg = 'black')
        
        ## Define conditions for the buttons (text, height, width, background color, function that button calls)
        self.button1 = tk.Button(self.frame, text = 'Customize', height=3, width = 8, background = 'pink', command = self.new_window)
        self.runtimeButton = tk.Button(self.frame, text = 'Run Time', height =3, width =8,  background = 'orange', command=self.btnRuntime)
        self.startButton = tk.Button(self.frame, text = 'Set', height = 3, width =8,  background = 'green', command=self.btnstart)
        self.stopButton = tk.Button(self.frame, text = 'Stop', height = 3, width =8,  background = 'red', command=self.btnstop)
        self.loadButton = tk.Button(self.frame, text = 'Load next', height = 3, width =8,  background = 'yellow', command=self.btnload)
        
        ## define conditions for labels (text, font)
        self.label_4 = tk.Label(self.frame, text = rotation,font=labelFont)
        self.label_2 = Label(self.frame, text = temp,font=labelFont)
        self.label_3 = Label(self.frame, text = 'Degrees Celcuis',font=labelFont)
        self.label_5 = Label(self.frame, text = 'Degrees/Sec',font=labelFont)
        self.label_6 = Label(self.frame, text = angle,font=labelFont)
        self.label_7 = Label(self.frame, text = 'Degrees',font=labelFont)
        self.label_8 = Label(self.frame, text = dwell,font=labelFont)
        self.label_9 = Label(self.frame, text = 'Seconds',font=labelFont)
        self.label_10 = Label(self.frame, text = 'Setpoint',font=labelFont)
        self.label_11 = Label(self.frame, text = 'Rotation Speed',font=labelFont)
        self.label_12 = Label(self.frame, text = 'Angle of Rotation',font=labelFont)
        self.label_13 = Label(self.frame, text = 'Dwell Time',font=labelFont)
        
        ## setting font size of buttons
        self.startButton ['font'] = myFont
        self.stopButton ['font'] = myFont
        self.loadButton ['font'] = myFont
        self.runtimeButton ['font'] = myFont
        self.button1 ['font'] = myFont
        
        ## setting positions of buttons and labels (y position from starting from top, x potition starting from left)
        self.startButton.grid(row=0, column=15)
        self.runtimeButton.grid(row=0, column=0)
        self.stopButton.grid(row=15, column=15)
        self.loadButton.grid(row=15, column=0)
        self.button1.grid(row =15, column =9, columnspan=3)
        self.frame.grid(row = 800, column = 450)
        self.label_4.grid(row=1, column=10)
        self.label_2.grid(row=2, column=10)
        self.label_3.grid(row=2, column=11)
        self.label_5.grid(row=1, column=11)
        self.label_6.grid(row=3, column=10)
        self.label_7.grid(row=3, column=11)
        self.label_8.grid(row=4, column=10)
        self.label_9.grid(row=4, column=11)
        self.label_10.grid(row=2, column = 9)
        self.label_11.grid(row=1, column =9)
        self.label_12.grid(row=3, column =9)
        self.label_13.grid(row=4, column =9)

## function for the button that brings up the customization menu (the second menu)
    def new_window(self):
        self.newWindow = tk.Toplevel(self.master)
        self.app = Demo2(self.newWindow)

## button that sets all customized values to the working values and sets motor start position
    def btnstart (self):
        if True:
            
## Update label configurations so that it displays true working values
            self.label_2.config(text=temp)
            self.label_4.config(text=rotation)
            self.label_6.config(text=angle)
            self.label_8.config(text=dwell)

## set run time to true so that motor starts turning when runtime buton is pressed
            global runtime
            runtime = True

## move the motor half of the set rotational distance as to prepare it for continous rocking
            gpio.output(DIR,CCW)
            for x in np.arange(angle//3.6):
                print ('ĆCW')
                gpio.output(STEP,gpio.HIGH)
                sleep(((1.8)/(2*(rotation))))
                gpio.output(STEP,gpio.LOW)
                sleep(((1.8)/(2*(rotation))))
                
## turn the motor 1/6 distance as to allow a new clip to be accesible through the door
    def btnload (self):
        if True:
            gpio.output(DIR,CW)
            for x in np.arange(33):
                print ('CW')
                gpio.output(STEP,gpio.HIGH)
                sleep(.002)
                gpio.output(STEP,gpio.LOW)
                sleep(.002)
                
## Function defining stop button that stops the motor after it finished one complete rotation 
    def btnstop (self):
        if True:
            global runtime
            runtime = False
            
## defines the button function for runtime, this function continuously oscillates the motor at the paramaters set
    def btnRuntime (self):
        global runtime
        global temp
        global angle
   

        if (runtime):
            sleep(dwell)
            gpio.output(DIR,CW)
            for x in np.arange(angle//1.8):
                print ('ĆW')
                gpio.output(STEP,gpio.HIGH)
                sleep(((1.8)/(2*(rotation))))
                gpio.output(STEP,gpio.LOW)
                sleep(((1.8)/(2*(rotation))))
            
            sleep(dwell)
            gpio.output(DIR,CCW)
            for x in np.arange(angle//1.8):
                print ('CĆW')
                gpio.output(STEP,gpio.HIGH)
                sleep(((1.8)/(2*(rotation))))
                gpio.output(STEP,gpio.LOW)
                sleep(((1.8)/(2*(rotation))))
                
        root.after(10,self.btnRuntime)

## second screen that allows for detailed customization of the motor  control paramaters
class Demo2:
    def __init__(self, master):

## define global variables so they can be motified inside class
        global temp
        global rotation
        global angle
        global dwell
        global runtime
        
## set font sizes for buttons (myFont) and labels (labelFont)
        myFont = font.Font(size=25)
        labelFont = font.Font(size=15)

        self.master = master
        self.frame = tk.Frame(self.master, bg = 'black')
        self.quitButton = tk.Button(self.frame, text = 'Quit', height = 1, width = 37, background = 'pink', command = self.close_windows)
        self.rotationupButton = tk.Button(self.frame, text = '+',  height = 2, width =8, background = 'green', command=self.btnRotationup)
        self.rotationdownButton = tk.Button(self.frame, text = '-',  height = 2, width =8, background = 'red', command=self.btnRotationdown)
        self.tempupButton = tk.Button(self.frame, text = '+',  height = 2, width =6, background = 'green', command=self.btntempup)
        self.tempdownButton = tk.Button(self.frame, text = '-',  height = 2, width =6, background = 'red', command=self.btntempdown)
        self.tempup1Button = tk.Button(self.frame, text = '+',  height = 2, width =6, background = 'green', command=self.btntempup1)
        self.tempdown1Button = tk.Button(self.frame, text = '-',  height = 2, width =6, background = 'red', command=self.btntempdown1)
        self.tempup2Button = tk.Button(self.frame, text = '+',  height = 2, width =6, background = 'green', command=self.btntempup2)
        self.tempdown2Button = tk.Button(self.frame, text = '-',  height = 2, width =6, background = 'red', command=self.btntempdown2)
        self.rotationupButton = tk.Button(self.frame, text = '+',  height = 2, width =8, background = 'green', command=self.btnRotationup)
        self.rotationdownButton = tk.Button(self.frame, text = '-',  height = 2, width =8, background = 'red', command=self.btnRotationdown)
        self.angleupButton = tk.Button(self.frame, text = '+',  height = 2, width =8, background = 'green', command=self.btnAngleup)
        self.angledownButton = tk.Button(self.frame, text = '-',  height = 2, width =8, background = 'red', command=self.btnAngledown)
        self.dwellupButton = tk.Button(self.frame, text = '+',  height = 2, width =8, background = 'green', command=self.btnDwellup)
        self.dwelldownButton = tk.Button(self.frame, text = '-',  height = 2, width =8, background = 'red', command=self.btnDwelldown)
        self.label_4 = tk.Label(self.frame, text = rotation,font=labelFont)
        self.label_2 = Label(self.frame, text = temp,font=labelFont)
        self.label_3 = Label(self.frame, text = 'Degrees Celcuis',font=labelFont)
        self.label_5 = Label(self.frame, text = 'Degrees/Sec',font=labelFont)
        self.label_6 = Label(self.frame, text = angle,font=labelFont)
        self.label_7 = Label(self.frame, text = 'Degrees',font=labelFont)
        self.label_8 = Label(self.frame, text = dwell,font=labelFont)
        self.label_9 = Label(self.frame, text = 'Seconds',font=labelFont)
        self.label_10 = Label(self.frame, text = 'Setpoint',font=labelFont)
        self.label_11 = Label(self.frame, text = 'Rotation Speed',font=labelFont)
        self.label_12 = Label(self.frame, text = 'Angle of Rotation',font=labelFont)
        self.label_13 = Label(self.frame, text = 'Dwell Time',font=labelFont)
      
        self.quitButton ['font'] = myFont

      
        self.tempupButton.grid(row=4, column=2)
        self.tempdownButton.grid(row=6, column=2)
        self.tempup1Button.grid(row=4, column=3)
        self.tempdown1Button.grid(row=6, column=3)
        self.tempup2Button.grid(row=4, column=4)
        self.tempdown2Button.grid(row=6, column=4)
        self.rotationupButton.grid(row=3, column=15)
        self.rotationdownButton.grid(row=4, column=15)
        self.angleupButton.grid(row=6, column=15)
        self.angledownButton.grid(row=7, column=15)
        self.dwellupButton.grid(row=9, column=15)
        self.dwelldownButton.grid(row=10, column=15)
        self.quitButton.grid(row = 0, column =0, columnspan=21)
        self.frame.grid(row = 800, column = 480)
        self.label_4.grid(row=3, column=16)
        self.label_2.grid(row=5, column=3)
        self.label_3.grid(row=5, column=5)

        self.label_5.grid(row=3, column=17)
        self.label_6.grid(row=6, column=16)
        self.label_7.grid(row=6, column=17)
        self.label_8.grid(row=9, column=16)
        self.label_9.grid(row=9, column=17)
        self.label_10.grid(row=3, column = 3)
        self.label_11.grid(row=2, column =15)
        self.label_12.grid(row=5, column =15)
        self.label_13.grid(row=8, column =15)
       
       
    def close_windows(self):
        self.master.destroy()

    def btnRotationup (self):
        if True:
            global rotation
            rotation += 5
            print (rotation)
            self.label_4.config(text=rotation)
        else:
            print ('nope')
        
    def btnRotationdown (self):
        if True:
            global rotation
            rotation -= 5
            print (rotation)
            self.label_4.config(text=rotation)
        else:
            print ('nope')

    def btntempup2 (self):
        if True:
            global temp
            x= Decimal('0.1')
            y = temp + x
            temp = y
            print (temp)
            self.label_2.config(text=temp)
        else:
            print ('nope')

    def btntempup1 (self):
        if True:
            global temp
            temp += 1
            print (temp)
            self.label_2.config(text=temp)
        else:
            print ('nope')
    def btntempup (self):
        if True:
            global temp
            temp += 10
            print (temp)
            self.label_2.config(text=temp)
        else:
            print ('nope')
    def btntempdown (self):
        if True:
            global temp
            temp -= 10
            print (temp)
            self.label_2.config(text=temp)
        else:
            print ('nope')
    def btntempdown1 (self):
        if True:
            global temp
            temp -= 1
            print (temp)
            self.label_2.config(text=temp)
        else:
            print ('nope')
    def btntempdown2 (self):
        if True:
            global temp
            x= Decimal('0.1')
            y = temp - x
            temp = y
            print (temp)
            self.label_2.config(text=temp)
        else:
            print ('nope')
        

    def btnAngleup (self):
        if True:
            global angle
            angle += 15
            print (angle)
            self.label_6.config(text=angle)
        else:
            print ('nope')
    def btnAngledown (self):
        if True:
            global angle
            angle -= 15
            print (angle)
            self.label_6.config(text=angle)
        else:
            print ('nope')
        
    def btnDwellup (self):
        if True:
            global dwell
            dwell += 1
            print (dwell)
            self.label_8.config(text=dwell)
        else:
            print ('nope')
        
    def btnDwelldown (self):
        if True:
            global dwell
            dwell -= 1
            print (dwell)
            self.label_8.config(text=dwell)
        else:
            print ('nope')



def main(): 

    ##root.configure(bg='black')
    ##root.geometry('800x480')
    app = Demo1(root)
    ##app = Demo2(root)
    root.mainloop()
    

if __name__ == '__main__':
    main()