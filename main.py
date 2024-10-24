#!/usr/bin/env python3

import csv
import logging
import os
import sys
import time
from collections import deque

from pms5003 import PMS5003, ReadTimeoutError

# Logging configuration
logging.basicConfig(
    format="%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Initialize sensor
pms5003 = PMS5003()
time.sleep(1.0)



# Constants
file_name = 'sensor_readings.csv'
TWELVE_HOURS = 12 * 3600
ONE_HOUR = 3600
TEN = 600
FIVE = 300
ONE = 60

# Start time
start_time = time.time()

# Function to read and process sensor data
def read_sensor_data():
    readings = pms5003.read()
    timestamp = time.time()
    pm1_0 = round(readings.pm_ug_per_m3(1.0), 2)
    pm2_5 = round(readings.pm_ug_per_m3(2.5), 2)
    pm10 = round(readings.pm_ug_per_m3(10), 2)
    
    return timestamp, pm1_0, pm2_5, pm10

# Function to display readings in terminal
def display_readings(pm1_0, pm2_5, pm10):
    sys.stdout.write("\033[H\033[J")  # Clear screen
    sys.stdout.write("                        Particulate Sensor!\n\n\n")
    sys.stdout.write(f"Live Sensor Readings  -  PM1.0: {pm1_0}       PM2.5: {pm2_5}        PM10: {pm10}\n\n\n")

    # Display runtime
    elapsed_time = time.time() - start_time
    elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
    sys.stdout.write(f"\033[999;0HRuntime: {elapsed_str}")
    sys.stdout.flush()

# Main function to run the sensor readings
def main():
    with open(file_name, mode='a', newline='') as file:
        writer = csv.writer(file)
        
        # Write header if file is new
        if os.stat(file_name).st_size == 0:
            write_csv_header(writer)

        try:
            while True:
                try:
                    timestamp, pm1_0, pm2_5, pm10 = read_sensor_data()

                    # Display current readings
                    display_readings(pm1_0, pm2_5, pm10)

                except ReadTimeoutError:
                    logging.error("Read timeout, reinitializing PMS5003 sensor")
                    global pms5003
                    pms5003 = PMS5003()

                time.sleep(1)

        except KeyboardInterrupt:
            logging.info("Program interrupted. Exiting...")

if __name__ == "__main__":
    main()
