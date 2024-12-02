#!/bin/bash

# Name of the Python script to execute
SCRIPT_NAME="run_tp3.py"

# Run the Python script and pass any command-line arguments, redirect output to benchmark.log and console
python3 "$SCRIPT_NAME" 

# Keep the terminal open to view the output
echo "Execution completed. Press Enter to exit."
read  # Wait for the user to press Enter before closing the terminal
