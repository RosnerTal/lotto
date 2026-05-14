import sqlite3
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import os
from datetime import datetime

# Initialize Firebase Admin
# NOTE: To run this locally, you need a service account key.
# Download from Firebase Console: Project Settings -> Service Accounts -> Generate new private key
# Save it as 'service-account.json' in this directory.
SERVICE_ACCOUNT_FILE = 'service-account.json'

if os.path.exists(SERVICE_ACCOUNT_FILE):
    cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
    firebase_admin.initialize_app(cred)
else:
    # Try to initialize with default credentials (useful for Cloud Run/App Engine)
    try:
        firebase_admin.initialize_app()
    except Exception as e:
        print("Error: Could not initialize Firebase Admin. Please provide service-account.json.")
        exit(1)

db_firestore = firestore.client()

def migrate():
    if not os.path.exists('lottery.db'):
        print("Error: lottery.db not found.")
        return

    # Connect to SQLite
    conn = sqlite3.connect('lottery.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT draw_number, draw_date, number1, number2, number3, 
               number4, number5, number6, strong_number
        FROM lottery_results
    """)
    rows = cursor.fetchall()

    print(f"Found {len(rows)} records in SQLite. Migrating to Firestore...")

    batch = db_firestore.batch()
    count = 0
    total_migrated = 0

    for row in rows:
        draw_number = row[0]
        data = {
            'draw_number': draw_number,
            'draw_date': row[1],
            'numbers': [row[2], row[3], row[4], row[5], row[6], row[7]],
            'strong_number': row[8],
            'updated_at': firestore.SERVER_TIMESTAMP
        }

        doc_ref = db_firestore.collection('draws').document(str(draw_number))
        batch.set(doc_ref, data)
        
        count += 1
        total_migrated += 1

        if count >= 400:  # Firestore batch limit is 500
            batch.commit()
            print(f"Migrated {total_migrated} records...")
            batch = db_firestore.batch()
            count = 0

    if count > 0:
        batch.commit()
    
    print(f"Migration complete! Total migrated: {total_migrated}")
    conn.close()

if __name__ == "__main__":
    migrate()
