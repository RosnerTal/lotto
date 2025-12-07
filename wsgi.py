"""
WSGI configuration for PythonAnywhere
"""
import sys
import os

# Add your project directory to the path
project_home = '/home/trosner/lotto'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variable to indicate PythonAnywhere
os.environ['PYTHONANYWHERE_DOMAIN'] = 'pythonanywhere.com'

from app import app as application

