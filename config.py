"""
Configuration for the Lottery Application
"""
import os

# Detect if running on PythonAnywhere
IS_PYTHONANYWHERE = 'PYTHONANYWHERE_DOMAIN' in os.environ

# Database configuration
if IS_PYTHONANYWHERE:
    # MySQL on PythonAnywhere
    DB_TYPE = 'mysql'
    MYSQL_CONFIG = {
        'host': 'trosner.mysql.pythonanywhere-services.com',
        'user': 'trosner',
        'password': 'Xhknrhkhui',
        'database': 'trosner$lottery',  # PythonAnywhere format: username$dbname
    }
else:
    # SQLite for local development
    DB_TYPE = 'sqlite'
    SQLITE_PATH = 'lottery.db'

