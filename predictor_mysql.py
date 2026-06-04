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
    
    # Helper methods for statistical filtering
    def passes_filters(self, numbers: List[int], prev_numbers: List[int]) -> bool:
        sorted_nums = sorted(numbers)
        
        # 1. Sum constraint (80-150 covers 86.8% of draws)
        s = sum(sorted_nums)
        if not (80 <= s <= 150):
            return False
            
        # 2. Odd/Even split (2/4, 3/3, 4/2 covers 79.9% of draws)
        odds = sum(1 for n in sorted_nums if n % 2 != 0)
        if odds not in (2, 3, 4):
            return False
            
        # 3. High/Low split (2/4, 3/3, 4/2 covers 80.8% of draws)
        lows = sum(1 for n in sorted_nums if n <= 18)
        if lows not in (2, 3, 4):
            return False
            
        # 4. Consecutive pairs (0 or 1 covers 82.4% of draws)
        consecutives = 0
        for i in range(len(sorted_nums) - 1):
            if sorted_nums[i+1] - sorted_nums[i] == 1:
                consecutives += 1
        if consecutives > 1:
            return False
            
        # 5. Repeats from previous draw (0, 1, or 2 covers 95.4% of draws)
        if prev_numbers:
            prev_set = set(prev_numbers)
            repeats = len(prev_set.intersection(set(sorted_nums)))
            if repeats > 2:
                return False
                
        # 6. Gaps checks (avoid clusters, max gap between 5 and 18)
        gaps = [sorted_nums[i+1] - sorted_nums[i] for i in range(len(sorted_nums)-1)]
        max_gap = max(gaps) if gaps else 0
        min_gap = min(gaps) if gaps else 0
        if max_gap > 18 or max_gap < 5:
            return False
        if min_gap > 4:
            return False
            
        return True

    def get_valid_prediction(self, generate_base_func) -> Tuple[List[int], int]:
        draws = self.get_all_numbers(limit=1)
        prev_numbers = draws[0] if draws else []
        
        # Save state to ensure reproducibility for seed
        rand_state = random.getstate()
        
        # Try generating candidates until one passes
        found = False
        numbers = []
        for _ in range(1000):  # limit to prevent infinite loop
            numbers, _ = generate_base_func(bypass_filters=True)
            if self.passes_filters(numbers, prev_numbers):
                found = True
                break
                
        random.setstate(rand_state)
        
        if not found:
            # Fallback if no candidate passed
            numbers, _ = generate_base_func(bypass_filters=True)
            
        # Select strong number using overdue strong numbers model
        strongs = self.get_all_strong_numbers()
        last_seen = {i: 0 for i in range(1, 8)}
        for idx, sn in enumerate(strongs):
            if sn in last_seen and last_seen[sn] == 0:
                last_seen[sn] = idx
                
        sorted_overdue_sn = sorted(last_seen.items(), key=lambda x: x[1], reverse=True)
        strong_number = random.choice([sorted_overdue_sn[0][0], sorted_overdue_sn[1][0]])
        
        return sorted(numbers), strong_number

    # Prediction strategies with filters and candidate generation
    def predict_frequency_based(self, bypass_filters=False) -> Tuple[List[int], int]:
        if not bypass_filters:
            return self.get_valid_prediction(self.predict_frequency_based)
        hot_numbers = self.get_hot_numbers(top_n=15, recent_draws=100)
        if len(hot_numbers) >= 6:
            return random.sample(hot_numbers, 6), 1
        else:
            return hot_numbers + random.sample([i for i in range(1, 38) if i not in hot_numbers], 6 - len(hot_numbers)), 1

    def predict_balanced(self, bypass_filters=False) -> Tuple[List[int], int]:
        if not bypass_filters:
            return self.get_valid_prediction(self.predict_balanced)
        hot_numbers = self.get_hot_numbers(top_n=12, recent_draws=50)
        cold_numbers = self.get_cold_numbers(top_n=12, recent_draws=50)
        selected = random.sample(hot_numbers, min(len(hot_numbers), 3)) + random.sample(cold_numbers, min(len(cold_numbers), 3))
        while len(selected) < 6:
            num = random.randint(1, 37)
            if num not in selected: selected.append(num)
        return selected[:6], 1

    def predict_overdue(self, bypass_filters=False) -> Tuple[List[int], int]:
        if not bypass_filters:
            return self.get_valid_prediction(self.predict_overdue)
        overdue = self.get_overdue_numbers(top_n=15)
        overdue_numbers = [num for num, _ in overdue]
        if len(overdue_numbers) >= 6:
            return random.sample(overdue_numbers, 6), 1
        else:
            return overdue_numbers + random.sample([i for i in range(1, 38) if i not in overdue_numbers], 6 - len(overdue_numbers))[:6], 1

    def predict_pattern_based(self, bypass_filters=False) -> Tuple[List[int], int]:
        if not bypass_filters:
            return self.get_valid_prediction(self.predict_pattern_based)
        # Select numbers with standard odd/even pattern (e.g. 3 odd, 3 even)
        odds = random.sample([i for i in range(1, 38) if i % 2 != 0], 3)
        evens = random.sample([i for i in range(1, 38) if i % 2 == 0], 3)
        return odds + evens, 1

    def predict_statistical_average(self, bypass_filters=False) -> Tuple[List[int], int]:
        if not bypass_filters:
            return self.get_valid_prediction(self.predict_statistical_average)
        freq = self.frequency_analysis()
        if not freq: return random.sample(range(1, 38), 6), 1
        avg_freq = sum(freq.values()) / len(freq)
        candidates = [num for num, count in freq.items() if abs(count - avg_freq) <= avg_freq * 0.35]
        if len(candidates) < 6:
            candidates = list(range(1, 38))
        return random.sample(candidates, 6), 1

    def predict_recent_trends(self, bypass_filters=False) -> Tuple[List[int], int]:
        if not bypass_filters:
            return self.get_valid_prediction(self.predict_recent_trends)
        recent_draws = self.get_all_numbers(limit=15)
        flat = [num for draw in recent_draws for num in draw]
        recent_freq = Counter(flat)
        trending = [num for num, _ in recent_freq.most_common(16)]
        return random.sample(trending, 6), 1

    def predict_number_pairs(self, bypass_filters=False) -> Tuple[List[int], int]:
        if not bypass_filters:
            return self.get_valid_prediction(self.predict_number_pairs)
        recent_draws = self.get_all_numbers(limit=100)
        pairs = []
        for draw in recent_draws:
            for i in range(len(draw)):
                for j in range(i + 1, len(draw)):
                    pairs.append(tuple(sorted([draw[i], draw[j]])))
        top_pairs = Counter(pairs).most_common(20)
        pair_numbers = []
        for pair, _ in top_pairs:
            for num in pair:
                if num not in pair_numbers:
                    pair_numbers.append(num)
        selected = random.sample(pair_numbers, min(len(pair_numbers), 4))
        others = [i for i in range(1, 38) if i not in selected]
        selected += random.sample(others, 2)
        return selected, 1

    def predict_sum_based(self, bypass_filters=False) -> Tuple[List[int], int]:
        if not bypass_filters:
            return self.get_valid_prediction(self.predict_sum_based)
        return random.sample(range(1, 38), 6), 1

    def predict_odd_even_balanced(self, bypass_filters=False) -> Tuple[List[int], int]:
        if not bypass_filters:
            return self.get_valid_prediction(self.predict_odd_even_balanced)
        recent_draws = self.get_all_numbers(limit=50)
        odd_f, even_f = Counter(), Counter()
        for draw in recent_draws:
            for n in draw:
                if n % 2 == 0: even_f[n] += 1
                else: odd_f[n] += 1
        numbers = random.sample([n for n, _ in odd_f.most_common(12)], 3) + random.sample([n for n, _ in even_f.most_common(12)], 3)
        return numbers, 1

    def predict_spread_distribution(self, bypass_filters=False) -> Tuple[List[int], int]:
        if not bypass_filters:
            return self.get_valid_prediction(self.predict_spread_distribution)
        segment_size = 37 / 6
        numbers = []
        freq = self.frequency_analysis(limit=100)
        for i in range(6):
            start, end = int(i * segment_size) + 1, int((i + 1) * segment_size)
            seg_nums = {k: v for k, v in freq.items() if start <= k <= end}
            top_seg = sorted(seg_nums.items(), key=lambda x: x[1], reverse=True)[:3]
            if top_seg:
                numbers.append(random.choice([item[0] for item in top_seg]))
            else:
                numbers.append(random.randint(start, min(end, 37)))
        while len(set(numbers)) < 6:
            numbers.append(random.randint(1, 37))
        return list(set(numbers)), 1
    
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
        """Generate multiple predictions (1-10)."""
        strategies = [
            ("Frequency Based (Hot Numbers)", self.predict_frequency_based),
            ("Balanced (Hot & Cold)", self.predict_balanced),
            ("Overdue Numbers", self.predict_overdue),
            ("Pattern Based", self.predict_pattern_based),
            ("Statistical Average", self.predict_statistical_average),
            ("Recent Trends", self.predict_recent_trends),
            ("Number Pairs Analysis", self.predict_number_pairs),
            ("Sum-Based Targeting", self.predict_sum_based),
            ("Odd/Even Balanced", self.predict_odd_even_balanced),
            ("Spread Distribution", self.predict_spread_distribution),
        ]
        
        # Limit to 10 predictions max
        num_predictions = min(num_predictions, 10)
        
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

