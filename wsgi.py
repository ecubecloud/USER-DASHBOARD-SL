#!/usr/bin/env python3
"""
WSGI configuration for StarLink Dashboard
This file is used by web servers to serve your Flask application
"""
import sys
import os

# Add your project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import your Flask application
from server import app as application

if __name__ == "__main__":
    application.run(host='0.0.0.0', port=5000)
