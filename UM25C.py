#!/usr/bin/python
"""
Code partly taken from crackleware on Github
https://github.com/crackleware/um25c_bluetooth_receiver
"""

"""

Based on the reverse engineering at https://sigrok.org/wiki/RDTech_UM_series

#* All byte offsets are in decimal, and inclusive. All values are big-endian and unsigned.

Ensure that the bluetooth switch on the UM25C is On. Specify the Mac Address of the tester as a commandline argument 
or edit it in this script. If a commandline argument is detected, the address given in the code is ignored.

Use the send_command function to send an instruction to the Tester. Commands are defined as constants.

You can edit what happens in the collect function.

#! Dependencies setup

sudo apt install libbluetooth-dev
pip install git+https://github.com/pybluez/pybluez@4d46ce1

"""


import sys
import struct
import time
import threading
import bluetooth

DEVICE_ADDRESS = "Default"
SLEEP_INTERVAL = 0.3 # Collection Interval in seconds 

STOP_COLLECTING = False # DO NOT CHANGE THIS

try:
    DEVICE_ADDRESS = sys.argv[1]
except IndexError:
    if DEVICE_ADDRESS == "Default":
        print("Device Address is not specified as an argument or in code. Aborting")
        sys.exit()

NEXT_SCREEN = 0xF1
ROTATE_SCREEN = 0xF2
PREVIOUS_SCREEN = 0xF3
CLEAR_CURRENT_DATAGROUP = 0xF4

SET_DATA_GROUP_0 = 0xA0
SET_DATA_GROUP_1 = 0xA1
SET_DATA_GROUP_2 = 0xA2
SET_DATA_GROUP_3 = 0xA3
SET_DATA_GROUP_4 = 0xA4
SET_DATA_GROUP_5 = 0xA5
SET_DATA_GROUP_6 = 0xA6
SET_DATA_GROUP_7 = 0xA7
SET_DATA_GROUP_8 = 0xA8
SET_DATA_GROUP_9 = 0xA9

SET_THRESHOLD_AMPERAGE_0 = 0XB0 # 0.00
SET_THRESHOLD_AMPERAGE_1 = 0XB1 # 0.01
SET_THRESHOLD_AMPERAGE_2 = 0XB2
SET_THRESHOLD_AMPERAGE_3 = 0XB3
SET_THRESHOLD_AMPERAGE_4 = 0XB4
SET_THRESHOLD_AMPERAGE_5 = 0XB5
SET_THRESHOLD_AMPERAGE_6 = 0XB6
SET_THRESHOLD_AMPERAGE_7 = 0XB7
SET_THRESHOLD_AMPERAGE_8 = 0XB8
SET_THRESHOLD_AMPERAGE_9 = 0XB9
SET_THRESHOLD_AMPERAGE_10 = 0XBA
SET_THRESHOLD_AMPERAGE_11 = 0XBB
SET_THRESHOLD_AMPERAGE_12 = 0XBC
SET_THRESHOLD_AMPERAGE_13 = 0XBD
SET_THRESHOLD_AMPERAGE_14 = 0XBE
SET_THRESHOLD_AMPERAGE_15 = 0XBF
SET_THRESHOLD_AMPERAGE_16 = 0XC0
SET_THRESHOLD_AMPERAGE_17 = 0XC1
SET_THRESHOLD_AMPERAGE_18 = 0XC2
SET_THRESHOLD_AMPERAGE_19 = 0XC3
SET_THRESHOLD_AMPERAGE_20 = 0XC4
SET_THRESHOLD_AMPERAGE_21 = 0XC5
SET_THRESHOLD_AMPERAGE_22 = 0XC6
SET_THRESHOLD_AMPERAGE_23 = 0XC7
SET_THRESHOLD_AMPERAGE_24 = 0XC8
SET_THRESHOLD_AMPERAGE_25 = 0XC9
SET_THRESHOLD_AMPERAGE_26 = 0XCA
SET_THRESHOLD_AMPERAGE_27 = 0XCB
SET_THRESHOLD_AMPERAGE_28 = 0XCC
SET_THRESHOLD_AMPERAGE_29 = 0XCD
SET_THRESHOLD_AMPERAGE_30 = 0XCE # 0.30

SET_BACKLIGHT_LEVEL_0 = 0xD0
SET_BACKLIGHT_LEVEL_1 = 0xD1
SET_BACKLIGHT_LEVEL_2 = 0xD2
SET_BACKLIGHT_LEVEL_3 = 0xD3
SET_BACKLIGHT_LEVEL_4 = 0xD4
SET_BACKLIGHT_LEVEL_5 = 0xD5

SET_SCREENSAVER_DISABLED = 0xE0
SET_SCREENSAVER_TIME_1_MINUTES = 0xE1
SET_SCREENSAVER_TIME_2_MINUTES = 0xE2
SET_SCREENSAVER_TIME_3_MINUTES = 0xE3
SET_SCREENSAVER_TIME_4_MINUTES = 0xE4
SET_SCREENSAVER_TIME_5_MINUTES = 0xE5
SET_SCREENSAVER_TIME_6_MINUTES = 0xE6
SET_SCREENSAVER_TIME_7_MINUTES = 0xE7
SET_SCREENSAVER_TIME_8_MINUTES = 0xE8
SET_SCREENSAVER_TIME_9_MINUTES = 0xE9

def connect_to_usb_tester(bt_addr):
    sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    sock.connect((bt_addr, 1))
    sock.settimeout(1.0)
    for _ in range(10):
        try:
            read_data(sock)
        except bluetooth.BluetoothError as e:
            time.sleep(0.2)
        else:
            break
    else:
        raise e
    return sock

def read_data(sock):
    sock.send(bytes([0xF0]))
    d = bytes()
    while len(d) < 130:
        d += sock.recv(1024)
    return d

def read_measurements(sock):
    d = read_data(sock)
    
    voltage_in_volts, current_in_amps, power_in_watts = [x / 1000 for x in struct.unpack("!HHI", d[2:10])]
    current_in_amps = current_in_amps/10
    temp_celsius, temp_fahrenheit = struct.unpack("!HH", d[10:14])
    selected_data_group = (struct.unpack("!H", d[14:16]))[0]
    
    array = [x for x in struct.unpack("!"+("I"*20),d[16:96])]
    cumulative_mwh_mah_of_datagroups_as_list_of_tuples = [(array[i], array[i+1]) for i in range(len(array))]
    usb_data_pos_voltage, usb_data_neg_voltage = [x / 100 for x in struct.unpack("!HH", d[96:100])]
    charging_mode = (struct.unpack("!H", d[100]))[0]
    mAh, mWh = [x for x in struct.unpack("!II", d[102:110])]
    configured_amperage_recording_threshold = (struct.unpack("!H", d[110:112]))[0] / 100
    duration_of_threshold_recording_in_cumulative_seconds = (struct.unpack("!I", d[112:116]))[0]
    threshold_record_isactive = (struct.unpack("!H", d[116:118]))[0]
    current_screentimeout_in_minutes = (struct.unpack("!H", d[118:120]))[0] # From 0-9
    current_backlight_setting = (struct.unpack("!H", d[120:122]))[0] # From 0-5
    resistance_in_ohms = (struct.unpack("!I", d[122:126]))[0]
    current_screen_on_device = (struct.unpack("!H", d[126:128]))[0]
    
    del sock
    del d
    del array
    
    return locals()

def send_command(command: int, sock):
    sock.send(bytes([command]))

def collect(interval: float):
    global STOP_COLLECTING
    global DEVICE_ADDRESS
    
    sock = connect_to_usb_tester(DEVICE_ADDRESS)
    
    commands = [SET_BACKLIGHT_LEVEL_3, SET_DATA_GROUP_5, SET_SCREENSAVER_DISABLED]
    for command in commands:
        send_command(command, sock)
        
    while not STOP_COLLECTING:
        try:
            d = read_measurements(sock)
        except bluetooth.BluetoothError as e:
            time.sleep(0.2)
            continue
        except Exception as e:
            print(e)
            continue

        # Replace the print statement with whatever logging you want.
        print(d)
        time.sleep(interval)
    
    sock.close()

if __name__ == "__main__":
    try:
        print("\nPress Enter to stop Collection of power data\n")
        time.sleep(1)
        thread = threading.Thread(target=collect, args=[SLEEP_INTERVAL])
        thread.start()
    except Exception as e:
            print(e)
    else:
        input()

"""
All data returned by the device consists of measurements and configuration status, in 130-byte chunks. To my knowledge, it will never send any other data. All bytes below are displayed in hex format; every command is a single byte.

# Commands to send:

F0 - Request new data dump; this triggers a 130-byte response
F1 - (device control) Go to next screen
F2 - (device control) Rotate screen
F3 - (device control) Go to previous screen

F4 - (device control) Clear data group
Ax - (device control) Set the Data group (0xA0-0xA9)

Bx - (configuration) Set recording threshold to a value between 0.00 and 0.15 A (where 'x' in the byte is 4 bits representing the value after the decimal point, eg. B7 to set it to 0.07 A)
Cx - (configuration) Same as Bx, but for when you want to set it to a value between 0.16 and 0.30 A (16 subtracted from the value behind the decimal point, eg. 0.19 A == C3)

Dx - (configuration) Set device backlight level; 'x' must within [0xD0 - 0xD5]
Ex - (configuration) Set screen timeout ('screensaver'); 'x' is in minutes and must be between 0 and 9 (inclusive), where 0 disables the screensaver

# Response format:
All byte offsets are in decimal, and inclusive. All values are big-endian and unsigned.
0   - 1   Start marker (always 0x09c9 for the UM25C)
2   - 3   Voltage (in mV, divide by 1000 to get V)
4   - 5   Amperage (in 0.1 mA, divide by 10000 to get A)
6   - 9   Wattage (in mW, divide by 1000 to get W)
10  - 11  Temperature (in celsius)
12  - 13  Temperature (in fahrenheit)
14  - 15  Currently selected data group
16  - 95  Array of main capacity data groups (where the first one, group 0, is the ephemeral one)
            -- for each data group: 4 bytes mAh, 4 bytes mWh
96  - 97  USB data line voltage (positive) in centivolts (divide by 100 to get V)
98  - 99  USB data line voltage (negative) in centivolts (divide by 100 to get V)
100 - 101 Charging mode; this is an enum, details for which are given on the sigrok site.
102 - 105 mAh from threshold-based recording
106 - 109 mWh from threshold-based recording
110 - 111 Currently configured threshold for recording (in cA, divide by 100 to get A)
112 - 115 Duration of recording, in seconds since start
116 - 117 Recording active (1 if recording 0 if not) in cumulative seconds
118 - 119 Current screen timeout setting (0-9 where 0 is no screen timeout)
120 - 121 Current backlight setting
122 - 125 Resistance in deci-ohms (divide by 10 to get ohms)
126 - 127  Current screen (zero-indexed, same order as on device)
128 - 129 Stop marker (always 0xfff1)
"""

"""
To connect to the Testers : 

sudo systemctl start bluetooth
sudo bluetoothctl
# power on
# scan on
# pair ###BTADDR###
# trust ###BTADDR###
python3 UM25C.py ###BTADDR###
You can also manually set the bluetooth address of the device as a string, that variable is placed just after the imports. 
"""

"""
Known models
The Android app uses the first two bytes to determine the model number. The following models are known:

ID	Model
0x0963	UM24C
0x09c9	UM25C
0x0d4c	UM34C

Charging modes
Not all devices support detection of all listed charging modes, but the index between devices is consistent (e.g. index 1 will always be QC2).

Index	Display	Meaning
0	UNKNOWN	Unknown, or normal (non-custom mode)
1	QC2	Qualcomm Quick Charge 2.0
2	QC3	Qualcomm Quick Charge 3.0
3	APP2.4A	Apple, max 2.4 Amp
4	APP2.1A	Apple, max 2.1 Amp
5	APP1.0A	Apple, max 1.0 Amp
6	APP0.5A	Apple, max 0.5 Amp
7	DCP1.5A	Dedicated Charging Port, max 1.5 Amp (D+ to D- short)
8	SAMSUNG	Samsung (Adaptive Fast Charging?)

Unknown response fields

Bytes 128+129 are not entirely known yet. They are believed to be stop markers.
On UM24C and UM25C, all observed units seem to be 0xfff1 so far.
"""
