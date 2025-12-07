"""
MySQL Predictor adapter for PythonAnywhere deployment
"""
import MySQLdb
from collections import Counter
from typing import List, Tuple, Dict
import random
import hashlib
from config import MYSQL_CONFIG


class LotteryPredictorMySQL:
    # Only use data from the last 4 years
    DATE_FILTER = "draw_date >= DATE_SUB(CURDATE(), INTERVAL 4 YEAR)"
    
    # Filter for current lottery system
    CURRENT_SYSTEM_FILTER = """
        strong_number <= 7 
        AND number1 <= 37 AND number2 <= 37 AND number3 <= 37 
        AND number4 <= 37 AND number5 <= 37 AND number6 <= 37
    """
    
    def __init__(self):
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Connect to MySQL database."""
        self.conn = MySQLdb.connect(
            host=MYSQL_CONFIG['host'],
            user=MYSQL_CONFIG['user'],
            passwd=MYSQL_CONFIG['password'],
            db=MYSQL_CONFIG['database'],
            charset='utf8mb4'
        )
        self.cursor = self.conn.cursor()
    
    def close(self):
        """Close the database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def get_all_numbers(self, limit: int = None) -> List[List[int]]:
        """Get all main numbers from the database."""
        if limit:
            query = f"""
                SELECT number1, number2, number3, number4, number5, number6
                FROM lottery_results
                WHERE {self.CURRENT_SYSTEM_FILTER} AND {self.DATE_FILTER}
                ORDER BY draw_date DESC
                LIMIT %s
            """
            self.cursor.execute(query, (limit,))
        else:
            query = f"""
                SELECT number1, number2, number3, number4, number5, number6
                FROM lottery_results
                WHERE {self.CURRENT_SYSTEM_FILTER} AND {self.DATE_FILTER}
                ORDER BY draw_date DESC
            """
            self.cursor.execute(query)
        
        return [list(row) for row in self.cursor.fetchall()]
    
    def get_all_strong_numbers(self, limit: int = None) -> List[int]:
        """Get all strong numbers from the database."""
        if limit:
            query = f"""
                SELECT strong_number
                FROM lottery_results
                WHERE {self.CURRENT_SYSTEM_FILTER} AND {self.DATE_FILTER}
                ORDER BY draw_date DESC
                LIMIT %s
            """
            self.cursor.execute(query, (limit,))
        else:
            query = f"""
                SELECT strong_number
                FROM lottery_results
                WHERE {self.CURRENT_SYSTEM_FILTER} AND {self.DATE_FILTER}
                ORDER BY draw_date DESC
            """
            self.cursor.execute(query)
        
        return [row[0] for row in self.cursor.fetchall()]
    
    def frequency_analysis(self, limit: int = None) -> Dict[int, int]:
        """Analyze frequency of each number."""
        all_numbers = self.get_all_numbers(limit)
        flat_numbers = [num for draw in all_numbers for num in draw]
        return dict(Counter(flat_numbers))
    
    def strong_number_frequency(self, limit: int = None) -> Dict[int, int]:
        """Analyze frequency of strong numbers."""
        strong_numbers = self.get_all_strong_numbers(limit)
        return dict(Counter(strong_numbers))
    
    def get_hot_numbers(self, top_n: int = 10, recent_draws: int = 50) -> List[int]:
        """Get the most frequent numbers in recent draws."""
        freq = self.frequency_analysis(limit=recent_draws)
        sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [num for num, _ in sorted_freq[:top_n]]
    
    def get_cold_numbers(self, top_n: int = 10, recent_draws: int = 50) -> List[int]:
        """Get the least frequent numbers in recent draws."""
        freq = self.frequency_analysis(limit=recent_draws)
        all_numbers = {i: 0 for i in range(1, 38)}
        all_numbers.update(freq)
        sorted_freq = sorted(all_numbers.items(), key=lambda x: x[1])
        return [num for num, _ in sorted_freq[:top_n]]
    
    def get_overdue_numbers(self, top_n: int = 10) -> List[Tuple[int, int]]:
        """Get numbers that haven't appeared in a while."""
        self.cursor.execute(f"""
            SELECT number1, number2, number3, number4, number5, number6, draw_date
            FROM lottery_results
            WHERE {self.CURRENT_SYSTEM_FILTER} AND {self.DATE_FILTER}
            ORDER BY draw_date DESC
        """)
        
        results = self.cursor.fetchall()
        last_appearance = {i: 0 for i in range(1, 38)}
        
        for idx, row in enumerate(results):
            for num in row[:6]:
                if num in last_appearance and last_appearance[num] == 0:
                    last_appearance[num] = idx
        
        for num in last_appearance:
            if last_appearance[num] == 0:
                last_appearance[num] = len(results)
        
        sorted_overdue = sorted(last_appearance.items(), key=lambda x: x[1], reverse=True)
        return sorted_overdue[:top_n]
    
    def predict_frequency_based(self) -> Tuple[List[int], int]:
        """Predict using frequency analysis."""
        hot_numbers = self.get_hot_numbers(top_n=15, recent_draws=100)
        
        if len(hot_numbers) >= 6:
            numbers = sorted(random.sample(hot_numbers, 6))
        else:
            numbers = hot_numbers + random.sample(
                [i for i in range(1, 38) if i not in hot_numbers],
                6 - len(hot_numbers)
            )
            numbers = sorted(numbers)
        
        strong_freq = self.strong_number_frequency(limit=100)
        strong_number = max(strong_freq.items(), key=lambda x: x[1])[0]
        
        return numbers, strong_number
    
    def predict_balanced(self) -> Tuple[List[int], int]:
        """Predict using balanced approach."""
        hot_numbers = self.get_hot_numbers(top_n=10, recent_draws=50)
        cold_numbers = self.get_cold_numbers(top_n=10, recent_draws=50)
        
        selected = []
        if len(hot_numbers) >= 3:
            selected.extend(random.sample(hot_numbers, 3))
        else:
            selected.extend(hot_numbers)
        
        if len(cold_numbers) >= 3:
            selected.extend(random.sample(cold_numbers, 3))
        else:
            selected.extend(cold_numbers)
        
        while len(selected) < 6:
            num = random.randint(1, 37)
            if num not in selected:
                selected.append(num)
        
        numbers = sorted(selected[:6])
        
        strong_freq = self.strong_number_frequency()
        top_strong = sorted(strong_freq.items(), key=lambda x: x[1], reverse=True)[:3]
        strong_number = random.choice([num for num, _ in top_strong])
        
        return numbers, strong_number
    
    def predict_overdue(self) -> Tuple[List[int], int]:
        """Predict using overdue numbers."""
        overdue = self.get_overdue_numbers(top_n=12)
        overdue_numbers = [num for num, _ in overdue]
        
        if len(overdue_numbers) >= 6:
            numbers = sorted(random.sample(overdue_numbers, 6))
        else:
            numbers = overdue_numbers + random.sample(
                [i for i in range(1, 38) if i not in overdue_numbers],
                6 - len(overdue_numbers)
            )
            numbers = sorted(numbers[:6])
        
        strong_freq = self.strong_number_frequency()
        strong_number = min(strong_freq.items(), key=lambda x: x[1])[0]
        
        return numbers, strong_number
    
    def predict_pattern_based(self) -> Tuple[List[int], int]:
        """Predict using pattern analysis."""
        numbers = []
        
        even_count = random.choice([2, 3, 4])
        odd_count = 6 - even_count
        
        available_numbers = list(range(1, 38))
        random.shuffle(available_numbers)
        
        for num in available_numbers:
            if len(numbers) >= 6:
                break
            
            is_even = num % 2 == 0
            
            if is_even and even_count > 0:
                numbers.append(num)
                even_count -= 1
            elif not is_even and odd_count > 0:
                numbers.append(num)
                odd_count -= 1
        
        while len(numbers) < 6:
            num = random.randint(1, 37)
            if num not in numbers:
                numbers.append(num)
        
        numbers = sorted(numbers[:6])
        
        recent_strong = self.get_all_strong_numbers(limit=10)
        strong_number = random.choice(recent_strong) if recent_strong else random.randint(1, 7)
        
        return numbers, strong_number
    
    def predict_statistical_average(self) -> Tuple[List[int], int]:
        """Predict using statistical average."""
        freq = self.frequency_analysis()
        
        avg_freq = sum(freq.values()) / len(freq) if freq else 1
        
        candidates = []
        for num, count in freq.items():
            if abs(count - avg_freq) <= avg_freq * 0.3:
                candidates.append(num)
        
        if len(candidates) >= 6:
            numbers = sorted(random.sample(candidates, 6))
        else:
            numbers = candidates + random.sample(
                [i for i in range(1, 38) if i not in candidates],
                6 - len(candidates)
            )
            numbers = sorted(numbers[:6])
        
        strong_freq = self.strong_number_frequency()
        strong_avg = sum(strong_freq.values()) / len(strong_freq) if strong_freq else 1
        strong_candidates = [num for num, count in strong_freq.items() 
                           if abs(count - strong_avg) <= strong_avg * 0.3]
        strong_number = random.choice(strong_candidates) if strong_candidates else random.randint(1, 7)
        
        return numbers, strong_number
    
    def _set_variety_seed(self, variety: int, strategy_name: str):
        """Set random seed based on variety level."""
        if variety >= 100:
            return
        
        self.cursor.execute(f"""
            SELECT COUNT(*), MAX(draw_number) FROM lottery_results 
            WHERE {self.CURRENT_SYSTEM_FILTER} AND {self.DATE_FILTER}
        """)
        count, max_draw = self.cursor.fetchone()
        
        seed_string = f"{count}_{max_draw}_{strategy_name}"
        seed_hash = int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)
        
        if variety == 0:
            random.seed(seed_hash)
        else:
            random_component = random.randint(0, variety)
            mixed_seed = seed_hash + random_component
            random.seed(mixed_seed)
    
    def generate_predictions(self, num_predictions: int = 5, variety: int = 100) -> List[Dict]:
        """Generate multiple predictions."""
        strategies = [
            ("Frequency Based (Hot Numbers)", self.predict_frequency_based),
            ("Balanced (Hot & Cold)", self.predict_balanced),
            ("Overdue Numbers", self.predict_overdue),
            ("Pattern Based", self.predict_pattern_based),
            ("Statistical Average", self.predict_statistical_average),
        ]
        
        predictions = []
        for i in range(num_predictions):
            strategy_name, strategy_func = strategies[i % len(strategies)]
            self._set_variety_seed(variety, f"{strategy_name}_{i}")
            numbers, strong_number = strategy_func()
            
            predictions.append({
                "prediction_number": i + 1,
                "strategy": strategy_name,
                "numbers": numbers,
                "strong_number": strong_number
            })
        
        return predictions
    
    def get_statistics(self) -> Dict:
        """Get comprehensive statistics."""
        freq = self.frequency_analysis()
        strong_freq = self.strong_number_frequency()
        hot_numbers = self.get_hot_numbers(top_n=6, recent_draws=50)
        cold_numbers = self.get_cold_numbers(top_n=6, recent_draws=50)
        overdue = self.get_overdue_numbers(top_n=6)
        
        self.cursor.execute(f"""
            SELECT COUNT(*) FROM lottery_results 
            WHERE {self.CURRENT_SYSTEM_FILTER} AND {self.DATE_FILTER}
        """)
        total_draws = self.cursor.fetchone()[0]
        
        return {
            "total_draws": total_draws,
            "frequency_all_time": freq,
            "strong_number_frequency": strong_freq,
            "hot_numbers": hot_numbers,
            "cold_numbers": cold_numbers,
            "overdue_numbers": [num for num, _ in overdue],
            "most_common_number": max(freq.items(), key=lambda x: x[1]) if freq else (0, 0),
            "least_common_number": min(freq.items(), key=lambda x: x[1]) if freq else (0, 0),
            "most_common_strong": max(strong_freq.items(), key=lambda x: x[1]) if strong_freq else (0, 0),
            "least_common_strong": min(strong_freq.items(), key=lambda x: x[1]) if strong_freq else (0, 0),
        }

