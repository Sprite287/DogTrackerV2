#!/bin/bash
# To stop the Flask server, press Ctrl+C in the terminal where it is running.
echo "If the server is running in a separate window, close that window to stop the server."
read -p "Press any key to continue..."

pkill -f "flask run" 