"""
Automatic lottery result updater - runs every hour
Checks for new draws and imports them automatically
"""
import os
import sys
from datetime import datetime

# Auto-detect environment and use appropriate database
import threading
from database import LotteryDatabase, clear_results_cache
from predictor import clear_predictor_cache

from lotto_scraper import fetch_latest_result

LAST_AUTO_UPDATE_TIME = "Never"
_update_lock = threading.Lock()
_is_updating = False

def maybe_trigger_auto_update_async():
    """
    Checks if an auto-update check is due (> 2 hours since last check).
    If due, runs check_and_import_all_missing asynchronously in a background daemon thread.
    Non-blocking and safe to call on page loads.
    """
    global _is_updating
    if _is_updating:
        return
        
    def _worker():
        global _is_updating
        if not _update_lock.acquire(blocking=False):
            return
        try:
            _is_updating = True
            check_and_import_all_missing(force=False)
        except Exception as e:
            print(f"Background auto-updater error: {e}")
        finally:
            _is_updating = False
            _update_lock.release()
            
    threading.Thread(target=_worker, daemon=True).start()

def check_and_import_all_missing(force=False):
    """Check for new lottery results and import ALL missing draws"""
    global LAST_AUTO_UPDATE_TIME
    
    db = None
    try:
        # Get latest from database
        db = LotteryDatabase()
        db.connect()
        
        # Check throttling if not forced (2 hours / 7200 seconds)
        if not force:
            last_check_str = db.get_last_update_time()
            if last_check_str != "Never":
                try:
                    last_check_dt = datetime.strptime(last_check_str, "%Y-%m-%d %H:%M:%S")
                    time_diff = (datetime.now() - last_check_dt).total_seconds()
                    if time_diff < 7200:
                        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Skipping auto-update check (last check was {time_diff/60:.1f} minutes ago).")
                        LAST_AUTO_UPDATE_TIME = last_check_str
                        db.close()
                        return False
                except Exception as parse_err:
                    print(f"  [X] Error parsing last check time: {parse_err}")
        
        # Proceed with check
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] Checking for new lottery results...")
        
        latest_in_db = db.get_latest_draw_number()
        if not latest_in_db:
            latest_in_db = 0
        
        print(f"  Latest in database: Draw #{latest_in_db}")
        
        # 1. Fetch latest from website (HTML with CSV fallback)
        latest_result = fetch_latest_result()
        
        # 2. Additional fallback directly to official Pais CSV
        if not latest_result:
            print("  [!] fetch_latest_result returned None, attempting direct CSV fallback...")
            from lotto_excel_scraper import fetch_draws_excel
            csv_draws = fetch_draws_excel()
            if csv_draws and len(csv_draws) > 0:
                latest_result = csv_draws[0]
                
        if not latest_result:
            print("  [X] Failed to fetch latest draw from any online source")
            db.close()
            return False
        
        latest_online = latest_result['draw_number']
        print(f"  Latest online: Draw #{latest_online}")
        
        # Check if we need to import
        if latest_online > latest_in_db:
            start_draw = latest_in_db + 1
            missing_count = latest_online - start_draw + 1

            print(f"  [->] Found {missing_count} missing draw(s) (from #{start_draw} to #{latest_online})")
            
            missing_draws = []
            if missing_count == 1:
                # We already fetched the latest result, just use it
                missing_draws = [latest_result]
                print("  [OK] Using already fetched latest result")
            else:
                # Use official CSV scraper for multiple missing draws
                from lotto_excel_scraper import fetch_missing_draws_excel
                missing_draws = fetch_missing_draws_excel(start_draw, latest_online)
                if not missing_draws:
                    missing_draws = [latest_result]
            
            if not missing_draws:
                print("  [X] Failed to fetch missing draws")
                db.close()
                return False

            print(f"  [OK] Ready to import {len(missing_draws)} draw(s)")
            
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
                        print(f"  [OK] Imported Draw #{draw['draw_number']} ({draw['date']}): {draw['numbers']} + {draw['strong_number']}")
                    else:
                        failed.append(draw['draw_number'])
                        print(f"  [X] Failed to save Draw #{draw['draw_number']}")
                        
                except Exception as e:
                    failed.append(draw['draw_number'])
                    print(f"  [X] Error importing Draw #{draw['draw_number']}: {e}")
            
            # Invalidate caches
            clear_results_cache()
            clear_predictor_cache()
            
            # Save successful check time in Firestore
            LAST_AUTO_UPDATE_TIME = timestamp
            db.set_last_update_time(timestamp)
            db.close()
            
            print(f"\n  Summary:")
            print(f"    Imported: {len(imported)} draw(s)")
            if failed:
                print(f"    Failed: {len(failed)} draw(s) - {failed}")
            
            return len(imported) > 0
        else:
            print("  [OK] Database is up to date")
            LAST_AUTO_UPDATE_TIME = timestamp
            db.set_last_update_time(timestamp)
            db.close()
            return True
            
    except Exception as e:
        print(f"  [X] Error: {e}")
        if db:
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
    print("Checking for new results every day at 00:05 AM Israel Time")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    scheduler = BlockingScheduler(timezone='Asia/Jerusalem')
    
    # Run immediately on start
    check_and_import_all_missing()
    
    # Schedule to run every day at 00:05 AM
    scheduler.add_job(
        check_and_import_all_missing,
        'cron',
        hour=0,
        minute=5,
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

