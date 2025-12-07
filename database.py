import sqlite3
import csv
from datetime import datetime
from typing import List, Tuple, Optional


class LotteryDatabase:
    def __init__(self, db_name: str = "lottery.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Connect to the database."""
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
    
    def create_tables(self):
        """Create the lottery results table."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS lottery_results (
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
        """)
        
        # Create index for faster queries
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_draw_date 
            ON lottery_results(draw_date DESC)
        """)
        
        self.conn.commit()
    
    def import_from_csv(self, csv_file: str):
        """Import lottery results from CSV file, ignoring last two columns."""
        imported_count = 0
        skipped_count = 0
        
        # Try different encodings
        encodings = ['utf-8-sig', 'utf-8', 'windows-1255', 'iso-8859-8', 'cp1255', 'latin1']
        file_content = None
        
        for encoding in encodings:
            try:
                with open(csv_file, 'r', encoding=encoding) as file:
                    file_content = file.read()
                    break
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        if file_content is None:
            raise ValueError(f"Could not decode {csv_file} with any supported encoding")
        
        # Parse CSV from string
        csv_reader = csv.reader(file_content.splitlines())
        try:
            next(csv_reader)  # Skip header
        except StopIteration:
            pass
        
        for row in csv_reader:
            try:
                # Parse the row (ignoring last 2 columns)
                draw_number = int(row[0])
                draw_date = self._parse_date(row[1])
                numbers = [int(row[i]) for i in range(2, 8)]
                strong_number = int(row[8])
                
                # Insert into database
                self.cursor.execute("""
                    INSERT OR IGNORE INTO lottery_results 
                    (draw_number, draw_date, number1, number2, number3, 
                     number4, number5, number6, strong_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (draw_number, draw_date, *numbers, strong_number))
                
                if self.cursor.rowcount > 0:
                    imported_count += 1
                else:
                    skipped_count += 1
            
            except (ValueError, IndexError) as e:
                print(f"Error processing row {row}: {e}")
                skipped_count += 1
        
        self.conn.commit()
        return imported_count, skipped_count
    
    def _parse_date(self, date_str: str) -> str:
        """Parse date from DD/MM/YYYY format to YYYY-MM-DD."""
        try:
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            return date_str
    
    def add_result(self, draw_number: int, draw_date: str, 
                   numbers: List[int], strong_number: int) -> bool:
        """Add a new lottery result to the database."""
        try:
            # Validate input
            if len(numbers) != 6:
                raise ValueError("Must provide exactly 6 numbers")
            
            if not all(1 <= n <= 37 for n in numbers):
                raise ValueError("All numbers must be between 1 and 37")
            
            if not (1 <= strong_number <= 7):
                raise ValueError("Strong number must be between 1 and 7")
            
            # Parse date if needed
            if '/' in draw_date:
                draw_date = self._parse_date(draw_date)
            
            self.cursor.execute("""
                INSERT INTO lottery_results 
                (draw_number, draw_date, number1, number2, number3, 
                 number4, number5, number6, strong_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (draw_number, draw_date, *numbers, strong_number))
            
            self.conn.commit()
            return True
        
        except Exception as e:
            print(f"Error adding result: {e}")
            return False
    
    def get_all_results(self) -> List[Tuple]:
        """Get all lottery results ordered by date descending."""
        self.cursor.execute("""
            SELECT draw_number, draw_date, number1, number2, number3, 
                   number4, number5, number6, strong_number
            FROM lottery_results
            ORDER BY draw_date DESC
        """)
        return self.cursor.fetchall()
    
    def get_latest_results(self, limit: int = 10) -> List[Tuple]:
        """Get the latest N lottery results."""
        self.cursor.execute("""
            SELECT draw_number, draw_date, number1, number2, number3, 
                   number4, number5, number6, strong_number
            FROM lottery_results
            ORDER BY draw_date DESC
            LIMIT ?
        """, (limit,))
        return self.cursor.fetchall()
    
    def get_results_count(self) -> int:
        """Get total number of results in database."""
        self.cursor.execute("SELECT COUNT(*) FROM lottery_results")
        return self.cursor.fetchone()[0]
    
    def get_latest_draw_number(self) -> Optional[int]:
        """Get the latest draw number in the database."""
        self.cursor.execute("""
            SELECT draw_number 
            FROM lottery_results 
            ORDER BY draw_date DESC 
            LIMIT 1
        """)
        result = self.cursor.fetchone()
        return result[0] if result else None


def initialize_database(csv_file: str = "Lotto.csv"):
    """Initialize database and import CSV data."""
    db = LotteryDatabase()
    db.connect()
    
    print("Creating database tables...")
    db.create_tables()
    
    print(f"Importing data from {csv_file}...")
    imported, skipped = db.import_from_csv(csv_file)
    
    print(f"Import complete!")
    print(f"  - Imported: {imported} records")
    print(f"  - Skipped: {skipped} records")
    print(f"  - Total in database: {db.get_results_count()} records")
    
    db.close()
    return imported, skipped


if __name__ == "__main__":
    initialize_database()

