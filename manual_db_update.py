import os
from database import LotteryDatabase
from lotto_scraper import fetch_draw_result
import time

def manual_update():
    print("Starting manual database update for 2026 data...")
    db = LotteryDatabase()
    db.connect()
    
    latest_in_db = db.get_latest_draw_number()
    print(f"Latest draw in Firestore: #{latest_in_db}")
    
    target_latest = 3924
    
    if latest_in_db >= target_latest:
        print("Database is already up to date!")
        db.close()
        return

    missing_range = range(latest_in_db + 1, target_latest + 1)
    print(f"Fetching {len(missing_range)} missing draws: #{latest_in_db + 1} to #{target_latest}")
    
    imported_count = 0
    for draw_num in missing_range:
        print(f"  - Fetching Draw #{draw_num}...", end="", flush=True)
        try:
            result = fetch_draw_result(draw_num)
            if result and result.get('numbers'):
                success = db.add_result(
                    result['draw_number'],
                    result['date'],
                    result['numbers'],
                    result['strong_number']
                )
                if success:
                    print(" [OK]")
                    imported_count += 1
                else:
                    print(" [FAILED SAVE]")
            else:
                print(" [NO DATA FOUND]")
        except Exception as e:
            print(f" [ERROR: {e}]")
        
        time.sleep(0.5)
    
    print(f"\nManual Update Complete! Imported {imported_count} draws.")
    db.close()

if __name__ == "__main__":
    manual_update()
