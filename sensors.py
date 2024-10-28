#!/usr/bin/env python3

import logging
import time
import csv
import sys
import os
from pms5003 import PMS5003, ReadTimeoutError
from PIL import Image, ImageDraw, ImageFont
from st7735 import ST7735
from smbus2 import SMBus
from bme280 import BME280

# Logging configuration
logging.basicConfig(
    format="%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S")

# Initialize sensors
pms5003 = PMS5003()
bme280 = BME280(i2c_dev=SMBus(1))
time.sleep(1.0)

# Initialize ST7735 Display
disp = ST7735(
    port=0,
    cs=1,
    dc=9,
    backlight=12,
    rotation=270,
    spi_speed_hz=10000000
)
disp.begin()

# Constants
file_name = 'sensor_readings.csv'
UPDATE_INTERVAL = 5  # Update CSV every 30 seconds

# Screen dimensions
WIDTH = disp.width
HEIGHT = disp.height

# Font setup
font_size = 18
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', font_size)

# Start time
start_time = time.time()

# Define gradient thresholds for PM levels (example values)
PM_LEVELS = {
    'PM1.0': [1, 200, 1000],
    'PM2.5': [1, 200, 1000],
    'PM10': [1, 200, 1000]
}

# Gradient colors
COLOR_GREEN = (0, 255, 0)
COLOR_YELLOW = (255, 255, 0)
COLOR_RED = (255, 0, 0)

# Function to calculate color based on value
def calculate_color(value, levels):
    if value <= levels[0]:
        return COLOR_GREEN
    elif value <= levels[1]:
        # Gradient between green and yellow
        scale = (value - levels[0]) / (levels[1] - levels[0])
        return (
            int(COLOR_GREEN[0] + (COLOR_YELLOW[0] - COLOR_GREEN[0]) * scale),
            int(COLOR_GREEN[1] + (COLOR_YELLOW[1] - COLOR_GREEN[1]) * scale),
            int(COLOR_GREEN[2] + (COLOR_YELLOW[2] - COLOR_GREEN[2]) * scale)
        )
    elif value <= levels[2]:
        # Gradient between yellow and red
        scale = (value - levels[1]) / (levels[2] - levels[1])
        return (
            int(COLOR_YELLOW[0] + (COLOR_RED[0] - COLOR_YELLOW[0]) * scale),
            int(COLOR_YELLOW[1] + (COLOR_RED[1] - COLOR_YELLOW[1]) * scale),
            int(COLOR_YELLOW[2] + (COLOR_RED[2] - COLOR_YELLOW[2]) * scale)
        )
    return COLOR_RED

# Function to color text for the terminal using ANSI escape codes
def color_text_terminal(text, color):
    return f"\033[38;2;{color[0]};{color[1]};{color[2]}m{text}\033[0m"

# Function to write CSV header
def write_csv_header(writer):
    writer.writerow(["Timestamp", "PM1.0", "PM2.5", "PM10", "Temperature", "Pressure", "Humidity"])

# Function to read and process sensor data
def read_sensor_data():
    # PMS5003 readings
    readings = pms5003.read()
    pm1_0 = readings.pm_ug_per_m3(1.0)
    pm2_5 = readings.pm_ug_per_m3(2.5)
    pm10 = readings.pm_ug_per_m3(10)

    # BME280 readings
    temperature = bme280.get_temperature()
    pressure = bme280.get_pressure()
    humidity = bme280.get_humidity()
    
    timestamp = time.time()

    return timestamp, pm1_0, pm2_5, pm10, temperature, pressure, humidity

# Function to display readings in terminal and on ST7735
def display_readings(pm1_0, pm2_5, pm10, temperature, pressure, humidity):
    # Clear terminal
    sys.stdout.write("\033[H\033[J")

    # Determine color for each reading
    color_pm1_0 = calculate_color(pm1_0, PM_LEVELS['PM1.0'])
    color_pm2_5 = calculate_color(pm2_5, PM_LEVELS['PM2.5'])
    color_pm10 = calculate_color(pm10, PM_LEVELS['PM10'])

    # Display readings in terminal with color
    sys.stdout.write(color_text_terminal(f"PM1.0: {pm1_0}", color_pm1_0) + "\n")
    sys.stdout.write(color_text_terminal(f"PM2.5: {pm2_5}", color_pm2_5) + "\n")
    sys.stdout.write(color_text_terminal(f"PM10: {pm10}", color_pm10) + "\n")

    # Display BME280 readings in terminal (without color)
    sys.stdout.write(f"Temperature: {temperature:.2f} C\n")
    sys.stdout.write(f"Pressure: {pressure:.2f} hPa\n")
    sys.stdout.write(f"Humidity: {humidity:.2f} %\n\n")

    # Display runtime in terminal
    elapsed_time = time.time() - start_time
    elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
    sys.stdout.write(f"\033[999;0HRuntime: {elapsed_str}")
    sys.stdout.flush()

    # Draw on ST7735 display (only PM values)
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Display PM readings on ST7735 with color
    draw.text((0, 0), f"PM1.0: {pm1_0}", font=font, fill=color_pm1_0)
    draw.text((0, 20), f"PM2.5: {pm2_5}", font=font, fill=color_pm2_5)
    draw.text((0, 40), f"PM10: {pm10}", font=font, fill=color_pm10)
    draw.text((0, 60), f"            {elapsed_str}", font=font, fill=(255, 255, 255))

    # Update display
    disp.display(img)

# Main function to run the sensor readings
def main():
    with open(file_name, mode='a', newline='') as file:
        writer = csv.writer(file)
        
        # Write header if file is new
        if os.stat(file_name).st_size == 0:
            write_csv_header(writer)

        last_update_time = time.time()

        try:
            while True:
                try:
                    # Read sensor data
                    timestamp, pm1_0, pm2_5, pm10, temperature, pressure, humidity = read_sensor_data()

                    # Display current readings on terminal and only PM values on ST7735
                    display_readings(pm1_0, pm2_5, pm10, temperature, pressure, humidity)

                    # Write to CSV every 30 seconds
                    if time.time() - last_update_time >= UPDATE_INTERVAL:
                        writer.writerow([
                            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)),
                            pm1_0, pm2_5, pm10, temperature, pressure, humidity
                        ])
                        file.flush()
                        last_update_time = time.time()

                except ReadTimeoutError:
                    logging.error("Read timeout, reinitializing PMS5003 sensor")
                    global pms5003
                    pms5003 = PMS5003()

                time.sleep(1)

        except KeyboardInterrupt:
            logging.info("Program interrupted. Exiting...")

if __name__ == "__main__":
    main()

