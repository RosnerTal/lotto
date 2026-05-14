from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
import os
import threading
import traceback

app = Flask(__name__)

# Safety-wrapped imports
try:
    from database import LotteryDatabase
    from predictor import LotteryPredictor
    from lotto_scraper import fetch_latest_result
    DATABASE_READY = True
except Exception as e:
    DATABASE_READY = False
    os.environ['IMPORT_ERROR'] = f"{str(e)}\n{traceback.format_exc()}"


@app.route('/health')
def health():
    if not DATABASE_READY:
        return f"DATABASE_ERROR: {os.environ.get('IMPORT_ERROR', 'Unknown Error')}", 200
    return "LottoFire Status: DATABASE_READY", 200


@app.route('/')
def index():
    if not DATABASE_READY:
        return "Database Error - Please check logs", 500
    try:
        db = LotteryDatabase()
        db.connect()
        latest_results = db.get_latest_results(limit=10)
        db.close()
        
        predictor = LotteryPredictor()
        predictor.connect()
        stats = predictor.get_statistics()
        total_results = stats['total_draws']
        predictor.close()
        
        return render_template('index.html', 
                             total_results=total_results,
                             latest_results=latest_results)
    except Exception as e:
        return f"App Error: {str(e)}", 500

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if not DATABASE_READY: return "Error", 500
    num_predictions = 5
    variety = 0
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
    if not DATABASE_READY: return "Error", 500
    predictor = LotteryPredictor()
    predictor.connect()
    stats = predictor.get_statistics()
    predictor.close()
    return render_template('statistics.html', statistics=stats)

@app.route('/how-it-works')
def how_it_works():
    if not DATABASE_READY: return "Error", 500
    predictor = LotteryPredictor()
    predictor.connect()
    stats = predictor.get_statistics()
    total_draws = stats['total_draws']
    predictor.close()
    return render_template('how_it_works.html', total_draws=total_draws)

@app.route('/add_result', methods=['GET', 'POST'])
def add_result():
    if not DATABASE_READY: return "Error", 500
    ADD_RESULT_PASSWORD = "Xhknrhkhui"
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password != ADD_RESULT_PASSWORD:
            db = LotteryDatabase()
            db.connect()
            latest_draw = db.get_latest_draw_number()
            next_draw = (latest_draw + 1) if latest_draw else 1
            db.close()
            return render_template('add_result.html', error=True, message="Incorrect password!", next_draw=next_draw)
        
        try:
            draw_number = int(request.form['draw_number'])
            draw_date = request.form['draw_date']
            numbers = [int(request.form[f'number{i}']) for i in range(1, 7)]
            strong_number = int(request.form['strong_number'])
            
            db = LotteryDatabase()
            db.connect()
            success = db.add_result(draw_number, draw_date, numbers, strong_number)
            db.close()
            
            if success:
                return render_template('add_result.html', success=True, message="Result added successfully!")
            else:
                return render_template('add_result.html', error=True, message="Failed to add result.")
        except Exception as e:
            return render_template('add_result.html', error=True, message=f"Error: {str(e)}")
    
    db = LotteryDatabase()
    db.connect()
    latest_draw = db.get_latest_draw_number()
    next_draw = (latest_draw + 1) if latest_draw else 1
    db.close()
    return render_template('add_result.html', next_draw=next_draw)

@app.route('/history')
def history():
    if not DATABASE_READY: return "Error", 500
    page = request.args.get('page', 1, type=int)
    per_page = 50
    db = LotteryDatabase()
    db.connect()
    all_results = db.get_all_results()
    total_results = len(all_results)
    start = (page - 1) * per_page
    results = all_results[start : start + per_page]
    total_pages = (total_results + per_page - 1) // per_page
    db.close()
    return render_template('history.html', results=results, page=page, total_pages=total_pages, total_results=total_results)

@app.route('/api/cron/update')
def cron_update():
    auth_key = request.args.get('key')
    if auth_key != "Xhknrhkhui":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        from auto_updater import check_and_import_all_missing
        success = check_and_import_all_missing()
        return jsonify({"success": True, "message": "Cron job completed", "updates_found": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
