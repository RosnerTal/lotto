# 🎱 Israeli Lottery Predictor

An advanced lottery prediction application that analyzes historical Israeli Lottery results to generate data-driven predictions for future draws.

## Features

- 📊 **Data Analysis**: Analyzes 3+ years of historical lottery data
- 🎯 **Multiple Prediction Strategies**: 5 different algorithms including:
  - Frequency-based (Hot numbers)
  - Balanced approach (Hot & Cold numbers)
  - Overdue numbers
  - Pattern-based analysis
  - Statistical average
- 📈 **Comprehensive Statistics**: Track hot, cold, and overdue numbers
- 🌐 **Web Interface**: Beautiful, modern web UI
- 💻 **CLI Tool**: Command-line interface for quick access
- ➕ **Add New Results**: Easily update the database after each raffle
- 🗄️ **SQLite Database**: Fast, reliable data storage

## Installation

1. **Clone or download this repository**

2. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

3. **Initialize the database with historical data**:
```bash
python database.py
```

This will import all data from `Lotto.csv` into the SQLite database.

## Usage

### Web Interface

1. **Start the web server**:
```bash
python app.py
```

2. **Open your browser** and navigate to:
```
http://localhost:5000
```

3. **Features available in the web interface**:
   - **Home**: View recent results and statistics overview
   - **Predictions**: Generate lottery predictions using multiple strategies
   - **Statistics**: View detailed analysis of historical data
   - **History**: Browse all past lottery results
   - **Add Result**: Add new lottery results after each draw

### Command Line Interface (CLI)

Run the CLI tool:
```bash
python cli.py
```

**CLI Menu Options**:
1. Initialize/Import Database from CSV
2. Generate Predictions
3. View Statistics
4. Add New Result
5. View Recent Results
6. Exit

### Python API

You can also use the modules directly in your Python code:

```python
from database import LotteryDatabase
from predictor import LotteryPredictor

# Initialize database
db = LotteryDatabase()
db.connect()

# Add a new result
db.add_result(
    draw_number=3873,
    draw_date="02/12/2025",
    numbers=[5, 12, 18, 24, 31, 36],
    strong_number=4
)

# Generate predictions
predictor = LotteryPredictor()
predictor.connect()
predictions = predictor.generate_predictions(num_predictions=5)

for pred in predictions:
    print(f"Strategy: {pred['strategy']}")
    print(f"Numbers: {pred['numbers']}")
    print(f"Strong Number: {pred['strong_number']}")

predictor.close()
db.close()
```

## Israeli Lottery System

The Israeli Lottery (לוטו) works as follows:
- Select **6 numbers** from 1-37
- Select **1 strong number** (המספר החזק/נוסף) from 1-7

## Prediction Strategies

### 1. Frequency-Based (Hot Numbers)
Focuses on numbers that appear most frequently in recent draws. These "hot" numbers are statistically more common in the short term.

### 2. Balanced Approach
Combines both hot (frequent) and cold (rare) numbers for a balanced selection that covers different statistical patterns.

### 3. Overdue Numbers
Targets numbers that haven't appeared recently, based on the theory that overdue numbers are "due" to appear.

### 4. Pattern-Based
Analyzes patterns in recent draws such as even/odd distribution and high/low number balance to generate predictions.

### 5. Statistical Average
Selects numbers that appear with average frequency, avoiding extremes of too hot or too cold.

## Database Schema

The application uses SQLite with the following schema:

```sql
CREATE TABLE lottery_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draw_number INTEGER UNIQUE NOT NULL,
    draw_date DATE NOT NULL,
    number1 INTEGER NOT NULL,
    number2 INTEGER NOT NULL,
    number3 INTEGER NOT NULL,
    number4 INTEGER NOT NULL,
    number5 INTEGER NOT NULL,
    number6 INTEGER NOT NULL,
    strong_number INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## Automatic Updates (Recommended)

The app can automatically check for new lottery results every hour:

### Option 1: Run Standalone Auto-Updater

**Windows:**
```bash
python auto_updater.py
```
Or double-click `run_updater.bat`

**Linux/Mac:**
```bash
python3 auto_updater.py
```
Or: `chmod +x run_updater.sh && ./run_updater.sh`

This will:
- Check for new draws every hour
- Automatically import the latest draw
- Log all activity to console
- Keep running in the background

### Option 2: Run Once (Manual Check)

```bash
python auto_updater.py --once
```

This checks once and exits - useful for cron jobs or Task Scheduler.

### Option 3: Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily
4. Action: Start a program
5. Program: `python.exe`
6. Arguments: `C:\git\Lotto\auto_updater.py --once`
7. Start in: `C:\git\Lotto`

### Option 4: Linux Cron

```bash
crontab -e
# Add this line (checks every hour):
0 * * * * cd /path/to/lotto && python3 auto_updater.py --once
```

## Adding New Results Manually

If you prefer manual control, you can add results in three ways:

### Method 1: Web Interface
1. Navigate to "Add Result" in the web interface
2. Fill in the form with the draw number, date, and numbers
3. Click "Add Result"

### Method 2: CLI
1. Run `python cli.py`
2. Select option 4 (Add New Result)
3. Follow the prompts

### Method 3: Python Code
```python
from database import LotteryDatabase

db = LotteryDatabase()
db.connect()
db.add_result(
    draw_number=3873,
    draw_date="02/12/2025",  # DD/MM/YYYY
    numbers=[5, 12, 18, 24, 31, 36],
    strong_number=4
)
db.close()
```

## API Endpoints

The web application also provides REST API endpoints:

- `GET /api/predict?num=5` - Get predictions (default: 5)
- `GET /api/statistics` - Get statistics in JSON format

Example:
```bash
curl http://localhost:5000/api/predict?num=3
```

## File Structure

```
Lotto/
├── Lotto.csv                 # Historical lottery data
├── lottery.db               # SQLite database (created on first run)
├── database.py              # Database management module
├── predictor.py             # Prediction algorithms module
├── app.py                   # Flask web application
├── cli.py                   # Command-line interface
├── requirements.txt         # Python dependencies
├── README.md               # This file
├── templates/              # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── predict.html
│   ├── statistics.html
│   ├── add_result.html
│   └── history.html
└── static/                 # Static files
    └── style.css
```

## Requirements

- Python 3.7 or higher
- Flask 3.0.0
- Werkzeug 3.0.1

## Disclaimer

⚠️ **Important**: This application is for entertainment and educational purposes only. Lottery results are random and cannot be predicted with certainty. Past performance does not guarantee future results. Please gamble responsibly.

## License

This project is open source and available for personal and educational use.

## Support

For issues, questions, or contributions, please refer to the project repository.

---

**Good luck! 🍀**


