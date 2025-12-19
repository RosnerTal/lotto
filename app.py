from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
import os
import threading

# Auto-detect environment and use appropriate database
if 'PYTHONANYWHERE_DOMAIN' in os.environ:
    # Running on PythonAnywhere - use MySQL
    from database_mysql import LotteryDatabaseMySQL as LotteryDatabase
    from predictor_mysql import LotteryPredictorMySQL as LotteryPredictor
else:
    # Running locally - use SQLite
    from database import LotteryDatabase
    from predictor import LotteryPredictor

from lotto_scraper import fetch_latest_result

app = Flask(__name__)

# Auto-updater status
auto_updater_enabled = False
auto_updater_thread = None


@app.route('/')
def index():
    """Main page showing predictions and recent results."""
    db = LotteryDatabase()
    db.connect()
    
    # Get latest results for display
    latest_results = db.get_latest_results(limit=10)
    
    db.close()
    
    # Get the actual count of draws used for predictions (last 4 years)
    predictor = LotteryPredictor()
    predictor.connect()
    stats = predictor.get_statistics()
    total_results = stats['total_draws']  # This is the filtered count
    predictor.close()
    
    return render_template('index.html', 
                         total_results=total_results,
                         latest_results=latest_results)


@app.route('/predict', methods=['GET', 'POST'])
def predict():
    """Generate predictions."""
    num_predictions = 5
    variety = 0  # Default to deterministic
    
    if request.method == 'POST':
        num_predictions = int(request.form.get('num_predictions', 5))
        variety = int(request.form.get('variety', 0))
    
    predictor = LotteryPredictor()
    predictor.connect()
    
    predictions = predictor.generate_predictions(num_predictions, variety=variety)
    statistics = predictor.get_statistics()
    
    predictor.close()
    
    return render_template('predict.html', 
                         predictions=predictions,
                         statistics=statistics,
                         current_variety=variety,
                         current_num=num_predictions)


@app.route('/statistics')
def statistics():
    """Show detailed statistics."""
    predictor = LotteryPredictor()
    predictor.connect()
    
    stats = predictor.get_statistics()
    
    predictor.close()
    
    return render_template('statistics.html', statistics=stats)


@app.route('/add_result', methods=['GET', 'POST'])
def add_result():
    """Add a new lottery result (password protected)."""
    ADD_RESULT_PASSWORD = "Xhknrhkhui"
    
    if request.method == 'POST':
        # Check password first
        password = request.form.get('password', '')
        if password != ADD_RESULT_PASSWORD:
            db = LotteryDatabase()
            db.connect()
            latest_draw = db.get_latest_draw_number()
            next_draw = (latest_draw + 1) if latest_draw else 1
            db.close()
            return render_template('add_result.html', 
                                 error=True, 
                                 message="Incorrect password!",
                                 next_draw=next_draw)
        
        try:
            draw_number = int(request.form['draw_number'])
            draw_date = request.form['draw_date']
            
            numbers = [
                int(request.form['number1']),
                int(request.form['number2']),
                int(request.form['number3']),
                int(request.form['number4']),
                int(request.form['number5']),
                int(request.form['number6'])
            ]
            
            strong_number = int(request.form['strong_number'])
            
            db = LotteryDatabase()
            db.connect()
            
            success = db.add_result(draw_number, draw_date, numbers, strong_number)
            
            db.close()
            
            if success:
                return render_template('add_result.html', 
                                     success=True, 
                                     message="Result added successfully!")
            else:
                return render_template('add_result.html', 
                                     error=True, 
                                     message="Failed to add result. Please check your input.")
        
        except Exception as e:
            return render_template('add_result.html', 
                                 error=True, 
                                 message=f"Error: {str(e)}")
    
    # GET request - get next draw number
    db = LotteryDatabase()
    db.connect()
    latest_draw = db.get_latest_draw_number()
    next_draw = (latest_draw + 1) if latest_draw else 1
    db.close()
    
    return render_template('add_result.html', next_draw=next_draw)


@app.route('/history')
def history():
    """Show all lottery results."""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    db = LotteryDatabase()
    db.connect()
    
    all_results = db.get_all_results()
    total_results = len(all_results)
    
    # Paginate
    start = (page - 1) * per_page
    end = start + per_page
    results = all_results[start:end]
    
    total_pages = (total_results + per_page - 1) // per_page
    
    db.close()
    
    return render_template('history.html', 
                         results=results,
                         page=page,
                         total_pages=total_pages,
                         total_results=total_results)


@app.route('/api/predict')
def api_predict():
    """API endpoint to get predictions."""
    num_predictions = request.args.get('num', 5, type=int)
    variety = request.args.get('variety', 0, type=int)
    
    predictor = LotteryPredictor()
    predictor.connect()
    
    predictions = predictor.generate_predictions(num_predictions, variety=variety)
    
    predictor.close()
    
    return jsonify(predictions)


@app.route('/api/statistics')
def api_statistics():
    """API endpoint to get statistics."""
    predictor = LotteryPredictor()
    predictor.connect()
    
    stats = predictor.get_statistics()
    
    # Convert to JSON-serializable format
    stats_json = {
        "total_draws": stats["total_draws"],
        "hot_numbers": stats["hot_numbers"],
        "cold_numbers": stats["cold_numbers"],
        "overdue_numbers": stats["overdue_numbers"],
        "most_common_number": list(stats["most_common_number"]),
        "least_common_number": list(stats["least_common_number"]),
        "most_common_strong": list(stats["most_common_strong"]),
        "least_common_strong": list(stats["least_common_strong"]),
    }
    
    predictor.close()
    
    return jsonify(stats_json)


@app.route('/api/fetch_latest')
def api_fetch_latest():
    """API endpoint to fetch latest result from lottosheli.co.il"""
    result = fetch_latest_result()
    if result:
        return jsonify({"success": True, "data": result})
    else:
        return jsonify({"success": False, "error": "Failed to fetch latest result"}), 500


@app.route('/api/check_missing')
def api_check_missing():
    """Check for missing draws between last DB entry and latest online"""
    db = LotteryDatabase()
    db.connect()
    
    latest_in_db = db.get_latest_draw_number()
    if not latest_in_db:
        latest_in_db = 0
    
    db.close()
    
    # Fetch latest from website
    latest_result = fetch_latest_result()
    if not latest_result:
        return jsonify({"success": False, "error": "Failed to fetch latest from website"}), 500
    
    latest_online = latest_result['draw_number']
    
    missing_draws = []
    if latest_online > latest_in_db:
        missing_draws = list(range(latest_in_db + 1, latest_online + 1))
    
    return jsonify({
        "success": True,
        "latest_in_db": latest_in_db,
        "latest_online": latest_online,
        "missing_draws": missing_draws,
        "count": len(missing_draws)
    })


@app.route('/get_draw_info', methods=['GET'])
def get_draw_info():
    """Get draw date info from dropdown (doesn't fetch actual numbers)"""
    draw_number = request.args.get('draw_number', type=int)
    
    if not draw_number or draw_number <= 0:
        return jsonify({"success": False, "error": "Invalid draw number"}), 400
    
    from lotto_scraper import fetch_draw_result
    
    # Fetch to get date only (numbers will be wrong for historical draws)
    result = fetch_draw_result(draw_number)
    
    if result:
        return jsonify({
            "success": True,
            "draw_number": result['draw_number'],
            "date": result['date'],
            "note": "Numbers must be entered manually for historical draws"
        })
    else:
        return jsonify({"success": False, "error": "Draw not found"}), 404


@app.route('/import_missing', methods=['POST'])
def import_missing():
    """Import only the latest draw (password protected)"""
    ADD_RESULT_PASSWORD = "Xhknrhkhui"
    
    password = request.form.get('password', '')
    if password != ADD_RESULT_PASSWORD:
        return jsonify({"success": False, "error": "Incorrect password"}), 403
    
    db = LotteryDatabase()
    db.connect()
    
    latest_in_db = db.get_latest_draw_number()
    if not latest_in_db:
        latest_in_db = 0
    
    # Fetch latest from website
    latest_result = fetch_latest_result()
    if not latest_result:
        db.close()
        return jsonify({"success": False, "error": "Failed to fetch from website"}), 500
    
    latest_online = latest_result['draw_number']
    
    # Check if already up to date
    if latest_online <= latest_in_db:
        db.close()
        return jsonify({
            "success": True,
            "imported": [],
            "imported_count": 0,
            "message": "Database is already up to date!"
        })
    
    # Import ONLY the latest draw (the website can only show current draw's numbers)
    try:
        success = db.add_result(
            latest_result['draw_number'],
            latest_result['date'],
            latest_result['numbers'],
            latest_result['strong_number']
        )
        
        db.close()
        
        if success:
            still_missing = list(range(latest_in_db + 1, latest_online))
            return jsonify({
                "success": True,
                "imported": [latest_result['draw_number']],
                "imported_count": 1,
                "still_missing": still_missing,
                "message": f"Imported latest draw #{latest_result['draw_number']}. {len(still_missing)} older draw(s) need manual entry."
            })
        else:
            return jsonify({"success": False, "error": "Failed to save to database"}), 500
            
    except Exception as e:
        db.close()
        return jsonify({"success": False, "error": f"Error: {str(e)}"}), 500


@app.route('/api/auto_updater/status')
def auto_updater_status():
    """Get auto-updater status"""
    return jsonify({
        "enabled": auto_updater_enabled,
        "running": auto_updater_thread is not None and auto_updater_thread.is_alive()
    })


@app.route('/api/auto_updater/start', methods=['POST'])
def start_auto_updater():
    """Start the auto-updater"""
    global auto_updater_enabled, auto_updater_thread
    
    password = request.form.get('password', '')
    if password != "Xhknrhkhui":
        return jsonify({"success": False, "error": "Incorrect password"}), 403
    
    if auto_updater_enabled:
        return jsonify({"success": False, "error": "Auto-updater is already running"})
    
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from auto_updater import check_and_import_latest
        
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            check_and_import_latest,
            'interval',
            hours=1,
            id='lottery_updater'
        )
        scheduler.start()
        
        auto_updater_enabled = True
        
        # Run once immediately
        def run_first_check():
            check_and_import_latest()
        
        auto_updater_thread = threading.Thread(target=run_first_check)
        auto_updater_thread.start()
        
        return jsonify({
            "success": True,
            "message": "Auto-updater started! Will check every hour."
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/auto_updater/check_now', methods=['POST'])
def check_now():
    """Manually trigger a check"""
    password = request.form.get('password', '')
    if password != "Xhknrhkhui":
        return jsonify({"success": False, "error": "Incorrect password"}), 403
    
    try:
        from auto_updater import check_and_import_latest
        
        def run_check():
            check_and_import_latest()
        
        thread = threading.Thread(target=run_check)
        thread.start()
        
        return jsonify({
            "success": True,
            "message": "Check started in background"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


