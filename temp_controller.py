#notes
#Written by: Alex Lopez

#import serial

#change com7 to match comm port on raspi
#ser=serial.Serial('/dev/ttyUSB0', 115200, timeout=1)

#setting the address of the TEC
A1 = '0'
A2 = '2'

#buf is data recieved
#buf=['*','0','0','0','0','0','3','e','8','c','0','^'] #10 degrees buf data
#buf=['0','0','0','0','0','0','0','0','0','0','0','0'] empty buf
buf=['*','0','0','0','0','0','0','0','1','8','9','^'] #alarm buf test. b[3] and b[0] set, 9

#MAYBE NEED TO CHANGE 1,7 TO 1,9, COME BACK LATER TO CHECK
def hexc2dec(bufp):
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

def calc_checksum (AA1,AA2,CC1,CC2,DD1,DD2,DD3,DD4,DD5,DD6,DD7,DD8):
    command_string = [AA1,AA2,CC1,CC2,DD1,DD2,DD3,DD4,DD5,DD6,DD7,DD8]
    val=0
    for x in range (0,12):
        val += ord(command_string[x])
    val_hex=hex(val)
    SS1=val_hex[-2]
    SS2=val_hex[-1]
    return (SS1,SS2)

#switch statement to determine what the comand code to be used is
def command (Q1):
    if Q1 == '1':
        print ('Reading Input 1...\n')
        C1,C2='0','1'
        D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','0'
        S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
        bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
        print ('Send: ', bst)
#        for pn in range(0,16):
#            ser.write(bst[pn].encode())
#        for pn in range(0,12):
#            buf[pn]=ser.read(1)
        print ('Recieve: ', buf, '\n')
        temp1  = hexc2dec(buf) / 100
        print ('Temp1: ', temp1, ' C', '\n')

    elif Q1 == '2':
        print ('This command returns the set value determined by Input2 or as a fixed value set by communications. \n')
        C1,C2='0','3'
        D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','0'
        S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
        bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
        print ('Send: ', bst)
#        for pn in range(0,16):
#            ser.write(bst[pn].encode())
#        for pn in range(0,12):
#            buf[pn]=ser.read(1)
        print ('Recieve: ', buf, '\n')
        desired_temp  = hexc2dec(buf) / 100
        print ('Desired Control Value: ', desired_temp, ' C \n')

    elif Q1 == '3':
        print ('Reading Power Output... \n')
        C1,C2='0','2'
        D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','0'
        S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
        bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
        print ('Send: ', bst)
#        for pn in range(0,16):
#            ser.write(bst[pn].encode())
#        for pn in range(0,12):
#            buf[pn]=ser.read(1)
        print ('Recieve: ', buf, '\n')
        power=hexc2dec(buf)
        power_percent=power*100/511
        print ('Power Output: ', power_percent, ' % \n')


    elif Q1 == '4': #check to see of this works
        print ('Checking Alarm Status... \n')
        C1,C2='0','5'
        D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','0'
        S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
        bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
        print ('Send: ', bst)
#        for pn in range(0,16):
#            ser.write(bst[pn].encode())
#        for pn in range(0,12):
#            buf[pn]=ser.read(1)
        print ('Recieve: ', buf)
        alarm_int=int(hexc2dec(buf))
        alarm_list=[int(i) for i in bin(alarm_int)[2:]]
        while len(alarm_list) < 7:
            alarm_list.insert(0,0)
        print('\n Bit 0 = 1 means HIGH ALARM. \n', 'Bit 1 = 1 means LOW ALARM. \n','Bit 2 = 1 means COMPUTER CONTROLLED ALARM. \n','Bit 3 = 1 means OVER CURRENT DETECTED. \n', 'Bit 4 = 1 means OPEN INPUT1.\n', 'Bit 5 = 1 means OPEN INPUT2. \n', 'Bit 6 = 1 means DRIVER LOW INPUT VOLTAGE. \n')
        print('Bits: ', alarm_list, '\n')
        if alarm_list[6] == 1:  #b[0]
            print('High Alarm Detected \n')
        if alarm_list[5] == 1:  #b[1]
            print('Low Alarm Detected \n')
        if alarm_list[4] == 1:  #b[2]
            print('Computer Controlled Alarm Detected \n')
        if alarm_list[3] == 1:  #b[3]
            print('Over Current Detected \n')
        if alarm_list[2] == 1:  #b[4]
            print('Open Input 1 Detected \n')
        if alarm_list[1] == 1:  #b[5]
            print('Open Input 2 Detected \n')
        if alarm_list[0] == 1:  #b[3]
            print('Driver Low Input Voltage Detected\n4')
        
    elif Q1 == '5':
        print ('Reading Input 2... \n')
        C1,C2='0','6'
        D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','0'
        S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
        bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
        print ('Send: ', bst)
#        for pn in range(0,16):
#            ser.write(bst[pn].encode())
#        for pn in range(0,12):
#            buf[pn]=ser.read(1)
        print ('Recieve: ', buf, '\n')
        temp2  = hexc2dec(buf) / 100
        print ('Temp2: ', temp2, ' C', '\n')

    elif Q1 == '6':
        print ('This command detects output current in A/D counts')
        print ('Checking Output Current Counts...')
        C1,C2='0','7'
        D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','0'
        S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
        bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
        print ('Send: ', bst)
#        for pn in range(0,16):
#            ser.write(bst[pn].encode())
#        for pn in range(0,12):
#            buf[pn]=ser.read(1)
        print ('Recieve: ', buf, '\n')
        ad_counts=hexc2dec(buf)
        print('A/D Counts: ', ad_counts, '\n')

    elif Q1 == '7': #check to see if this works correctly
        print ('Alarm Type\n')
        alarm_type_r_or_w = input ('Would you like to change alarm type or read the current alarm type settings? \n Type 1 to Change Alarm Type \n Type 2 to Read the Current Alarm Type \n Type Anything Else to Exit \n')
        if alarm_type_r_or_w == '1':    #write
            C1,C2='2','8'
            alarm_type_write = input ('Change Alarm Type \n Type 1 for No Alarms \n Type 2 for Tracking Alarm Mode \n Type 3 for Fixed Alarm Mode \n Type 4 for Computer Controlled Alarm Mode (See Command: Alarm Latch Enable) \n Type Anything Else to Exit \n')
            if alarm_type_write == '1':     #write, no alarms, send 0
                print ('No Alarms \n')
                D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','0'
                S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
                bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
                print ('Send: ', bst)
#                for pn in range(0,16):
#                   ser.write(bst[pn].encode())
#                for pn in range(0,12):
#                   buf[pn]=ser.read(1)
                print ('Recieve: ', buf, '\n')
                print('Alarm Type Set to No Alarms \n')
            elif alarm_type_write == '2':       #write, tracking alarm, send 1
                print ('Tracking Alarm Mode \n')
                D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','1'
                S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
                bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
                print ('Send: ', bst)
#                for pn in range(0,16):
#                ser.write(bst[pn].encode())
#                for pn in range(0,12):
#                buf[pn]=ser.read(1)
                print ('Recieve: ', buf, '\n')
                print('Alarm Type Set to Tracking Alarm Mode \n')
            elif alarm_type_write == '3':       #write, fixed alarm, send 2
                print ('Fixed Alarm Mode \n')
                D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','2'
                S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
                bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
                print ('Send: ', bst)
#                for pn in range(0,16):
#                   ser.write(bst[pn].encode())
#                for pn in range(0,12):
#                   buf[pn]=ser.read(1)
                print ('Recieve: ', buf, '\n')
                print('Alarm Type Set to Tracking Alarm Mode \n')
            elif alarm_type_write == '4':       #write, comp controlled alarm, send 3
                print ('Computer Controlled Alarm Mode \n')
                D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','3'
                S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
                bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
                print ('Send: ', bst)
#                for pn in range(0,16):
#                   ser.write(bst[pn].encode())
#                for pn in range(0,12):
#                   buf[pn]=ser.read(1)
                print ('Recieve: ', buf, '\n')
                print('Alarm Type Set to Tracking Alarm Mode \n')
            else:
                pass
        elif alarm_type_r_or_w == '2':  #read
            print ('Reading Alarm Type... \n')
            C1,C2='4','1'
            D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','0'
            S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
            bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
            print ('Send: ', bst)
#            for pn in range(0,16):
#               ser.write(bst[pn].encode())
#            for pn in range(0,12):
#               buf[pn]=ser.read(1)
            print ('Recieve: ', buf, '\n')
            alarm_read=int(hexc2dec(buf))
            if alarm_read == 0:
                print('No Alarms \n')
            elif alarm_read == 1:
                print('Tracking Alarm Mode \n')
            elif alarm_read == 2:
                print('Fixed Alarm Mode \n')
            elif alarm_read == 3:
                print('Computer Controlled Alarm Mode \n')
            else:
                pass
        else:
            pass
    
    elif Q1 == '8':
        print ('This function tells the controller how the set-point will be communicated. \n')
        set_type_define_r_or_w = input ('Would you like to change or read the current set type defenition? \n Type 1 to Change Set Type \n Type 2 to Read Set Type \n Type Anything Else to Exit \n')
        if set_type_define_r_or_w == '1':
            C1,C2='2','9'
            set_type_define_write = input ('Change Set Type Define \n Type 1 to Change to Computer Communicated Set Value \n Type 2 to Change to Potentiometer Input \n Type 3 to change to 0 to 5 V Input \n Type 4 to Change to 0 to 20 mA Input \n Type 5 to Change to Differential Set: Desired Control Value = Temp2 + Computer Set \n Type Anything Else to Exit \n')  #Didnt put #6: set value from MP-2986 Display and KEyboard Accessory
            if set_type_define_write == '1':        #write, comp communicated, send 0
                D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','0'
                S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
                bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
                print ('Send: ', bst)
#                for pn in range(0,16):
#                ser.write(bst[pn].encode())
#                for pn in range(0,12):
#                buf[pn]=ser.read(1)
                print ('Recieve: ', buf, '\n')
                print ('Set Type Define Changed to Computer Communicated Set Value \n')
            elif set_type_define_write == '2':        #write, potentiometer, send 1
                D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','1'
                S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
                bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
                print ('Send: ', bst)
#                for pn in range(0,16):
#                ser.write(bst[pn].encode())
#                for pn in range(0,12):
#                buf[pn]=ser.read(1)
                print ('Recieve: ', buf, '\n')
                print ('Set Type Define Changed to Potentiometer Input \n')
            elif set_type_define_write == '3':        #write, 0 to 5 V, send 2
                D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','2'
                S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
                bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
                print ('Send: ', bst)
#                for pn in range(0,16):
#                ser.write(bst[pn].encode())
#                for pn in range(0,12):
#                buf[pn]=ser.read(1)
                print ('Recieve: ', buf, '\n')
                print ('Set Type Define Changed to 0 to 5 V Input \n')
            elif set_type_define_write == '4':        #write, 0 to 20 mA, send 3
                D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','3'
                S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
                bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
                print ('Send: ', bst)
#                for pn in range(0,16):
#                ser.write(bst[pn].encode())
#                for pn in range(0,12):
#                buf[pn]=ser.read(1)
                print ('Recieve: ', buf, '\n')
                print ('Set Type Define Changed to 0 to 20 mA Input \n')
            else:
                pass
        elif set_type_define_r_or_w == '2':
            print ('Reading Set Type Definition... \n')
            C1,C2='4','2'
            D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','0'
            S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
            bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
            print ('Send: ', bst)
#            for pn in range(0,16):
#               ser.write(bst[pn].encode())
#            for pn in range(0,12):
#               buf[pn]=ser.read(1)
            print ('Recieve: ', buf, '\n')
            set_type=int(hexc2dec(buf))
            if set_type == 0:
                print('Computer Communicated Set Value \n')
            elif set_type == 1:
                print('Potentiometer Input \n')
            elif set_type == 2:
                print('0 to 5 V Input \n')
            elif set_type == 3:
                print('Differential Set: Desired Control Value = Temp2 + Computer Set \n')
            else:
                pass
        else:
            pass

    
    elif Q1 == '9':
        print ('Sensor Type \n')
        sensor_type_r_or_w = input ('Would you like to change sensor type or read the current sensor type? \n Type 1 to Change Sensor Type \n Type 2 to Read the Current Sensor Type \n Type Anything Else to Exit \n')
        if sensor_type_r_or_w == '1':
            C1,C2='2','a'
            sensor_type_write = input ('Change Sensor Type \n Type 1 for TS141 5K \n Type 2 for TS67 or TS136 15K \n Type 3 for TS91 10K \n Type 4 for TS165 230K \n Typr 5 for TS104 50K \n Type 6 for YSI H TP53 10K \n Type Anything Else to Exit \n')
            if sensor_type_write == '1':        #write, 5k, send 0
                D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','0'
                S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
                bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
                print ('Send: ', bst)
#                for pn in range(0,16):
#                ser.write(bst[pn].encode())
#                for pn in range(0,12):
#                buf[pn]=ser.read(1)
                print ('Recieve: ', buf, '\n')
                print ('Sensor Type Changed to TS141 5K \n')
            elif sensor_type_write == '2':      #write, 15k, send 1
                D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','1'
                S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
                bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
                print ('Send: ', bst)
#                for pn in range(0,16):
#                ser.write(bst[pn].encode())
#                for pn in range(0,12):
#                buf[pn]=ser.read(1)
                print ('Recieve: ', buf, '\n')
                print ('Sensor Type Changed to  TS67 or TS136 15K \n')
            elif sensor_type_write == '3':      #write, ts91 10k, send 2
                D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','2'
                S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
                bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
                print ('Send: ', bst)
#                for pn in range(0,16):
#                ser.write(bst[pn].encode())
#                for pn in range(0,12):
#                buf[pn]=ser.read(1)
                print ('Recieve: ', buf, '\n')
                print ('Sensor Type Changed to TS91 10K \n')
            elif sensor_type_write == '4':      #write, 230k, send 3
                D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','3'
                S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
                bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
                print ('Send: ', bst)
#                for pn in range(0,16):
#                ser.write(bst[pn].encode())
#                for pn in range(0,12):
#                buf[pn]=ser.read(1)
                print ('Recieve: ', buf, '\n')
                print ('Sensor Type Changed to TS165 230K \n')
            elif sensor_type_write == '5':      #write, 50k, send 4
                D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','4'
                S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
                bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
                print ('Send: ', bst)
#                for pn in range(0,16):
#                ser.write(bst[pn].encode())
#                for pn in range(0,12):
#                buf[pn]=ser.read(1)
                print ('Recieve: ', buf, '\n')
                print ('Sensor Type Changed to TS104 50K \n')
            elif sensor_type_write == '6':      #write, ysi 10k, send 5
                D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','5'
                S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
                bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
                print ('Send: ', bst)
#                for pn in range(0,16):
#                ser.write(bst[pn].encode())
#                for pn in range(0,12):
#                buf[pn]=ser.read(1)
                print ('Recieve: ', buf, '\n')
                print ('Sensor Type Changed to YSI H TP53 10K \n')
            else:
                pass
        elif sensor_type_r_or_w == '2':
            print ('Reading Sensor Type... \n')
            C1,C2='4','3'
            D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','0'
            S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
            bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
            print ('Send: ', bst)
#            for pn in range(0,16):
#               ser.write(bst[pn].encode())
#            for pn in range(0,12):
#               buf[pn]=ser.read(1)
            print ('Recieve: ', buf, '\n')
            sensor_type=int(hexc2dec(buf))
            if sensor_type == 0:
                print('Current Sensor Type: TS141 5K \n')
            elif sensor_type == 1:
                print('Current Sensor Type: TS67 or TS136 15K \n')
            elif sensor_type == 2:
                print('Current Sensor Type: TS91 10K \n')
            elif sensor_type == 3:
                print('Current Sensor Type: TS165 230K \n')
            elif sensor_type == 4:
                print('Current Sensor Type: TS104 50K \n')
            elif sensor_type == 5:
                print('Current Sensor Type: YSI H TP53 10K \n')
            else:
                pass
        else:
            pass

    elif Q1 == '10':
        print ('Control Type \n')
        control_type_r_or_w = input ('Would you like to change control type or read the current control type? \n Type 1 to Change Control Type \n Type 2 to Read the Current Control Type \n Type Anything Else to Exit \n')
        if control_type_r_or_w == '1':
            C1,C2='2','b'
            control_type_write = input ('Change Control Type \n Type 1 for Deadband Control \n Type 2 for PID Control \n Type 3 for Computer Control \n Type Anything Else to Exit \n')
            if control_type_write == '1':        #write, deadband, send 0
                D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','0'
                S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
                bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
                print ('Send: ', bst)
#                for pn in range(0,16):
#                ser.write(bst[pn].encode())
#                for pn in range(0,12):
#                buf[pn]=ser.read(1)
                print ('Recieve: ', buf, '\n')
                print ('Control Type Set to Deadband Control \n')
            elif sensor_type_write == '2':      #write, PID, send 1
                D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','1'
                S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
                bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
                print ('Send: ', bst)
#                for pn in range(0,16):
#                ser.write(bst[pn].encode())
#                for pn in range(0,12):
#                buf[pn]=ser.read(1)
                print ('Recieve: ', buf, '\n')
                print ('Control Type Set to PID Control \n')
            elif sensor_type_write == '3':      #write, computer control, send 2
                D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','2'
                S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
                bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
                print ('Send: ', bst)
#                for pn in range(0,16):
#                ser.write(bst[pn].encode())
#                for pn in range(0,12):
#                buf[pn]=ser.read(1)
                print ('Recieve: ', buf, '\n')
                print ('Control Type Set to Computer Control \n')
            else:
                pass
        elif control_type_r_or_w == '2':
            print ('Reading Control Type... \n')
            C1,C2='4','4'
            D1,D2,D3,D4,D5,D6,D7,D8='0','0','0','0','0','0','0','0'
            S1,S2=calc_checksum(A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8)
            bst=['*',A1,A2,C1,C2,D1,D2,D3,D4,D5,D6,D7,D8,S1,S2,'\r']
            print ('Send: ', bst)
#            for pn in range(0,16):
#               ser.write(bst[pn].encode())
#            for pn in range(0,12):
#               buf[pn]=ser.read(1)
            print ('Recieve: ', buf, '\n')
            control_type=int(hexc2dec(buf))
            if control_type == 0:
                print('Current Control Type: Deadband Control \n')
            elif control_type == 1:
                print('Current Control Type: PID Control \n')
            elif control_type == 2:
                print('Current Control Type: Computer Control \n')
            else:
                pass
        else:
            pass

        

    elif Q1 == '11':
        print ('Output Polarity...')
        


    elif Q1 == '12':
        print ('Changing Power On/Off...')
        CC1='2'
        CC2='d'

    elif Q1 == '13':
        print ('Output Shutdown In Case of Alarm...')
        CC1='2'
        CC2='e'

    elif Q1 == '14': #need to add more for comp control
        print ('Fixed Desired Control Setting \n')
        desired_control_r_or_w = input ('Would you like to change the fixed desired control setting or read the current fixed desired control setting? \n Type 1 to Change the Fixed Desired Control Setting \n Type 2 to Read the Current Fixed Desired Control Setting \n Type Anything Else to Exit \n')
        if desired_control_r_or_w == '1':
            C1,C2='1','c'
            desired_temp = input ('Enter the desired control temperature \n')
        try:
            desired_temp = float(desired_temp)
        except:
            print ('Error: Not a valid number \n')
        if type(desired_temp) == float:
            desired_temp = desired_temp * 100
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
            print ('Send: ', bst)
#            for pn in range(0,16):
#               ser.write(bst[pn].encode())
#            for pn in range(0,12):
#               buf[pn]=ser.read(1)
            print ('Recieve: ', buf, '\n')

                

                
                

        

    elif Q1 == '15':
        print ('Changing Proportional Bandwidth...')
        CC1='1'
        CC2='d'

    elif Q1 == '16':
        print ('Changing Integral Gain...')
        CC1='1'
        CC2='e'

    elif Q1 == '17':
        print ('Changing Derivaive Gain...')
        CC1='1'
        CC2='f'

#Help center to find command codes needed
    elif ((Q1 == 'H') or (Q1 =='h')):
        print ('\n 1 = Input 1 (Read Temperature of Primary Resistor) \n 2 = Desired Control Value (set value) \n 3 = Power Output \n 4 = Alarm Status \n 5 = Input 2 \n 6 = Output Current Counts \n 7 = Alarm Type \n 8 = Set Type Define ("set temp" input definition) \n 9 = Sensor Type \n 10 = Control Type \n 11 = Control Output Polarity \n 12 = Power on/off \n 13 = Output Shutdown if Alarm \n 14 = Fixed Desired Control Setting \n 15 = Proportional Bandwidth \n 16 = Integral Gain \n 17 = Derivative Gain \n 18 = Low External Set Range \n 19 = High External Set Range \n 20 = Alarm Deadband \n')
        
#Error Message for an incorrect error code
    else:
        print ('Command Code Error')
    
            

#Main while loop
while (1):
    #Prompt user to determine Command codes
    Qx1= input  ('Choose Command Code, Type H for command codes \n')
    
    #Calls function CC to send data  
    command(Qx1)