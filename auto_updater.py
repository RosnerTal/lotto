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
from lotto_excel_scraper import fetch_missing_draws_excel


def check_and_import_all_missing():
    """Check for new lottery results and import ALL missing draws"""
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
        
        # Fetch latest from website to know the range
        latest_result = fetch_latest_result()
        
        if not latest_result:
            print("  ✗ Failed to fetch from website")
            db.close()
            return False
        
        latest_online = latest_result['draw_number']
        print(f"  Latest online: Draw #{latest_online}")
        
        # Check if we need to import
        if latest_online > latest_in_db:
            missing_count = latest_online - latest_in_db
            print(f"  → Found {missing_count} missing draw(s)")
            
            # Fetch ALL missing draws using Excel API
            print(f"  → Fetching draws {latest_in_db + 1} to {latest_online} using Excel API...")
            missing_draws = fetch_missing_draws_excel(latest_in_db + 1, latest_online)
            
            if not missing_draws:
                print("  ✗ Failed to fetch draws from Excel API")
                db.close()
                return False
            
            print(f"  ✓ Fetched {len(missing_draws)} draw(s)")
            
            # Import each draw
            imported = []
            failed = []
            
            for draw in sorted(missing_draws, key=lambda x: x['draw_number']):
                try:
                    success = db.add_result(
                        draw['draw_number'],
                        draw['date'],
                        draw['numbers'],
                        draw['strong_number']
                    )
                    
                    if success:
                        imported.append(draw['draw_number'])
                        print(f"  ✓ Imported Draw #{draw['draw_number']}: {draw['numbers']} + {draw['strong_number']}")
                    else:
                        failed.append(draw['draw_number'])
                        print(f"  ✗ Failed to save Draw #{draw['draw_number']}")
                        
                except Exception as e:
                    failed.append(draw['draw_number'])
                    print(f"  ✗ Error importing Draw #{draw['draw_number']}: {e}")
            
            db.close()
            
            print(f"\n  Summary:")
            print(f"    Imported: {len(imported)} draw(s)")
            if failed:
                print(f"    Failed: {len(failed)} draw(s) - {failed}")
            
            return len(imported) > 0
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
    result = check_and_import_all_missing()
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
    check_and_import_all_missing()
    
    # Schedule to run every hour
    scheduler.add_job(
        check_and_import_all_missing,
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

