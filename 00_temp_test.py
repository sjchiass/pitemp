import psutil
import random
import math
import subprocess
import time
import csv
import datetime
from gpiozero import CPUTemperature
import argparse
import os

parser = argparse.ArgumentParser(description="Stress test and log temperature")
parser.add_argument("file_prefix", type=str, help="name of file to output")
parser.add_argument("--duration", type=int, help='total duration in minutes', default=60)
parser.add_argument("--max_threads", type=int, help='max number of threads', default=4)
parser.add_argument("-a", "--case_under", action="store_true", help="the bottom of the case is on")
parser.add_argument("-b", "--case_frame", action="store_true", help="the case frame is on")
parser.add_argument("-c", "--case_cable", action="store_true", help="the cable-side panel is on")
parser.add_argument("-d", "--case_gpio", action="store_true", help="the gpio-side panel is on")
parser.add_argument("-m", "--top_solid", action="store_true", help="the top panel is on and solid")
parser.add_argument("-n", "--top_hole", action="store_true", help="the top panel is on and has a fan hole")
parser.add_argument("-o", "--top_intake", action="store_true", help="there is a fan on the case pulling air in")
parser.add_argument("-p", "--top_exhaust", action="store_true", help="there is a fan on the case pushing air out")
parser.add_argument("-x", "--heatsink_main", action="store_true", help="there is a heatsink on the main SoC")
parser.add_argument("-y", "--heatsink_sub", action="store_true", help="there is a heatsink on the secondary SoC")

args = parser.parse_args()

cpu = CPUTemperature()

# Run for {duration} * minutes
t_end = time.time() + 60 * args.duration

# Create a list of dummy flags in the correct order
dummies = [args.case_under, args.case_frame, args.case_cable,
            args.case_gpio, args.top_solid, args.top_hole,
            args.top_intake, args.top_exhaust, args.heatsink_main,
            args.heatsink_sub]

# Also labels
dummy_labels = ["case_under", "case_frame", "case_cable",
                "case_gpio", "top_solid", "top_hole",
                "top_intake", "top_exhaust", "heatsink_main",
                "heatsink_sub"]

def run_tests(test_time_limit, max_test_threads, csv_writer):
    # Previous test level
    # This is saved each iteration so that two load identical load levels
    # do not occur one afer the other
    previous_stress = 0

    while time.time() < test_time_limit:
        # This will generate random durations from 3s to 21s, with a
        # distribution that favours smaller numbers.
        duration = math.ceil(math.exp(1 + 2*random.random()))
        stress = random.choice(
            [x for x in range(max_test_threads+1)
             if x != previous_stress])
        previous_stress = stress
        
        # If no threads, sleep for a few seconds
        # Both of the subprocesses below run separately from Python,
        # so we can keep doing other stuff
        if stress == 0:
            print(f"sleep {duration} seconds ...")
            load = 0
            p = subprocess.Popen(["sleep", f"{duration}"])
        else:
            print(f"stress {stress} cpus for {duration} seconds ...")
            p = subprocess.Popen(["stress", "--cpu", f"{stress}", "--timeout", f"{duration}"])
        
        # While the above subprocess is running, record some
        # measurements
        while p.poll() is None:
            time.sleep(1)
            w.writerow([datetime.datetime.now(), psutil.cpu_percent(), cpu.temperature, stress])

# Determine active dummy variables
active_dummies = [y for x, y in zip(dummies, dummy_labels) if x]

# From the dummies build a filename
dummy_string = "".join([str(int(x)) for x in dummies])
file_path = f"./{args.file_prefix}_{dummy_string}.csv"

if os.path.isfile(file_path):
    print(f"[Startup] The file {file_path} already exists. It will be appended to.")
else:
    print(f"[Startup] The file {file_path} is a new one. It will be created.")

print(f"[Startup] Tests will be run with {', '.join(active_dummies)}")
print(f"[Startup] If this is not what you intended, Ctrl+C in the next 10 seconds.")
time.sleep(10)
print("[Startup] Starting script ...")

# If the file already exists, append to it
if os.path.isfile(file_path):
    with open(file_path, mode="a") as f:
        w = csv.writer(f)
        run_tests(test_time_limit=t_end,
            max_test_threads=args.max_threads,
            csv_writer=w)
else:
    with open(file_path, mode="w") as f:
        w = csv.writer(f)
        w.writerow(["datetime", "usage", "temp", "stress", "load"])
        run_tests(test_time_limit=t_end,
                max_test_threads=args.max_threads,
                csv_writer=w)

print("Done!")
