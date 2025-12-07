# Deployment Guide for PythonAnywhere

## Your Account Details
- **Username**: trosner
- **URL**: https://trosner.pythonanywhere.com
- **MySQL Host**: trosner.mysql.pythonanywhere-services.com
- **MySQL User**: trosner
- **MySQL Database**: trosner$lottery

---

## Step-by-Step Deployment

### Step 1: Create the MySQL Database

1. Go to **PythonAnywhere Dashboard** → **Databases** tab
2. Under "Create a database", enter: `lottery`
3. Click **Create**
4. This creates the database `trosner$lottery`

### Step 2: Upload Your Files

**Option A: Using the Web Interface**
1. Go to **Files** tab
2. Create a new directory: `/home/trosner/lotto`
3. Upload ALL these files to `/home/trosner/lotto/`:
   - `app.py`
   - `database.py`
   - `database_mysql.py`
   - `predictor.py`
   - `predictor_mysql.py`
   - `config.py`
   - `wsgi.py`
   - `setup_mysql.py`
   - `requirements.txt`
   - `Lotto.csv`
   - `templates/` folder (all HTML files)
   - `static/` folder (style.css)

**Option B: Using Git (recommended)**
1. Go to **Consoles** tab → **Bash**
2. Run:
```bash
cd ~
git clone https://github.com/YOUR_REPO/lotto.git
```

### Step 3: Install Dependencies

1. Go to **Consoles** tab → **Bash**
2. Run:
```bash
cd ~/lotto
pip3 install --user -r requirements.txt
```

### Step 4: Initialize the Database

1. In the same Bash console, run:
```bash
cd ~/lotto
python3 setup_mysql.py
```

You should see:
```
Setting up MySQL database...
Creating tables...
Importing data from CSV...
Setup complete!
  - Imported: 4448 records
```

### Step 5: Create the Web App

1. Go to **Web** tab
2. Click **Add a new web app**
3. Choose **Manual configuration** (NOT Flask)
4. Choose **Python 3.10**

### Step 6: Configure WSGI

1. In the **Web** tab, find **WSGI configuration file**
2. Click on the link (e.g., `/var/www/trosner_pythonanywhere_com_wsgi.py`)
3. **Delete everything** and paste:

```python
import sys
import os

# Add your project directory to the path
project_home = '/home/trosner/lotto'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variable
os.environ['PYTHONANYWHERE_DOMAIN'] = 'pythonanywhere.com'

from app import app as application
```

4. Click **Save**

### Step 7: Set Static Files

1. In the **Web** tab, scroll to **Static files**
2. Add:
   - **URL**: `/static/`
   - **Directory**: `/home/trosner/lotto/static`

### Step 8: Reload and Test

1. Click the green **Reload** button at the top of the Web tab
2. Visit: **https://trosner.pythonanywhere.com**

---

## Troubleshooting

### "No module named 'MySQLdb'"
```bash
pip3 install --user mysqlclient
```

### Database connection error
- Check that the database `trosner$lottery` exists in the Databases tab
- Verify the password in `config.py`

### 500 Internal Server Error
- Check the **Error log** in the Web tab
- Common fix: Reload the web app after any changes

### Static files not loading
- Make sure the static files path is correct: `/home/trosner/lotto/static`

---

## Updating the App

After making changes locally:

1. Upload changed files via Files tab (or `git pull`)
2. Go to Web tab
3. Click **Reload**

---

## Adding New Lottery Results

1. Go to https://trosner.pythonanywhere.com/add_result
2. Enter the password: `Xhknrhkhui`
3. Fill in the lottery result
4. Click Add Result

The database will be updated automatically!

