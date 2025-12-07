"""
Setup script for MySQL database on PythonAnywhere
Run this once after uploading files to initialize the database.
"""
import os
os.environ['PYTHONANYWHERE_DOMAIN'] = 'pythonanywhere.com'

from database_mysql import LotteryDatabaseMySQL

def setup():
    print("Setting up MySQL database...")
    
    db = LotteryDatabaseMySQL()
    db.connect()
    
    print("Creating tables...")
    db.create_tables()
    
    print("Importing data from CSV...")
    imported, skipped = db.import_from_csv('Lotto.csv')
    
    print(f"\nSetup complete!")
    print(f"  - Imported: {imported} records")
    print(f"  - Skipped: {skipped} records")
    
    # Verify
    count = db.get_results_count()
    print(f"  - Total in database: {count} records")
    
    db.close()

if __name__ == "__main__":
    setup()

