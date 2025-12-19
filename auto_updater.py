"""
Automatic lottery result updater - runs every hour
Checks for new draws and imports them automatically
"""
import os
import sys
from datetime import datetime

# Auto-detect environment and use appropriate database
if 'PYTHONANYWHERE_DOMAIN' in os.environ:
    from database_mysql import LotteryDatabaseMySQL as LotteryDatabase
else:
    from database import LotteryDatabase

from lotto_scraper import fetch_latest_result


def check_and_import_latest():
    """Check for new lottery results and import if available"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{timestamp}] Checking for new lottery results...")
    
    try:
        # Get latest from database
        db = LotteryDatabase()
        db.connect()
        
        latest_in_db = db.get_latest_draw_number()
        if not latest_in_db:
            latest_in_db = 0
        
        print(f"  Latest in database: Draw #{latest_in_db}")
        
        # Fetch latest from website
        latest_result = fetch_latest_result()
        
        if not latest_result:
            print("  ✗ Failed to fetch from website")
            db.close()
            return False
        
        latest_online = latest_result['draw_number']
        print(f"  Latest online: Draw #{latest_online}")
        
        # Check if we need to import
        if latest_online > latest_in_db:
            print(f"  → New draw found! Importing #{latest_online}...")
            
            success = db.add_result(
                latest_result['draw_number'],
                latest_result['date'],
                latest_result['numbers'],
                latest_result['strong_number']
            )
            
            if success:
                print(f"  ✓ Successfully imported Draw #{latest_online}")
                print(f"     Date: {latest_result['date']}")
                print(f"     Numbers: {latest_result['numbers']}")
                print(f"     Strong: {latest_result['strong_number']}")
                
                # Check if there are still missing draws
                if latest_online - latest_in_db > 1:
                    missing = list(range(latest_in_db + 1, latest_online))
                    print(f"  ⚠ Warning: Still missing {len(missing)} draw(s): {missing}")
                    print(f"     These need to be added manually via the web interface")
                
                db.close()
                return True
            else:
                print(f"  ✗ Failed to save to database")
                db.close()
                return False
        else:
            print("  ✓ Database is up to date")
            db.close()
            return False
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        try:
            db.close()
        except:
            pass
        return False


def run_once():
    """Run the check once and exit"""
    result = check_and_import_latest()
    sys.exit(0 if result else 1)


def run_scheduler():
    """Run the scheduler continuously"""
    from apscheduler.schedulers.blocking import BlockingScheduler
    
    print("=" * 60)
    print("Israeli Lottery Auto-Updater Started")
    print("=" * 60)
    print("Checking for new results every hour")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    scheduler = BlockingScheduler()
    
    # Run immediately on start
    check_and_import_latest()
    
    # Schedule to run every hour
    scheduler.add_job(
        check_and_import_latest,
        'interval',
        hours=1,
        id='lottery_updater',
        name='Check for new lottery results'
    )
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n\nAuto-updater stopped")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Israeli Lottery Auto-Updater')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--schedule', action='store_true', help='Run scheduler (default)')
    
    args = parser.parse_args()
    
    if args.once:
        run_once()
    else:
        run_scheduler()

