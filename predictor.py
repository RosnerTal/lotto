import sqlite3
from collections import Counter
from typing import List, Tuple, Dict
import random
import hashlib
from datetime import datetime, timedelta


class LotteryPredictor:
    # Only use data from the last 4 years
    DATE_FILTER = "draw_date >= date('now', '-4 years')"
    
    # Filter for current lottery system: main numbers 1-37, strong number 1-7
    CURRENT_SYSTEM_FILTER = """
        strong_number <= 7 
        AND number1 <= 37 AND number2 <= 37 AND number3 <= 37 
        AND number4 <= 37 AND number5 <= 37 AND number6 <= 37
    """
    
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
    
    def get_all_numbers(self, limit: int = None) -> List[List[int]]:
        """Get all main numbers from the database (last 4 years, current system only)."""
        if limit:
            query = f"""
                SELECT number1, number2, number3, number4, number5, number6
                FROM lottery_results
                WHERE {self.CURRENT_SYSTEM_FILTER} AND {self.DATE_FILTER}
                ORDER BY draw_date DESC
                LIMIT ?
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
        """Get all strong numbers from the database (last 4 years, current system only)."""
        if limit:
            query = f"""
                SELECT strong_number
                FROM lottery_results
                WHERE {self.CURRENT_SYSTEM_FILTER} AND {self.DATE_FILTER}
                ORDER BY draw_date DESC
                LIMIT ?
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
        """Get the most frequent numbers in recent draws (hot numbers)."""
        freq = self.frequency_analysis(limit=recent_draws)
        sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [num for num, _ in sorted_freq[:top_n]]
    
    def get_cold_numbers(self, top_n: int = 10, recent_draws: int = 50) -> List[int]:
        """Get the least frequent numbers in recent draws (cold numbers)."""
        freq = self.frequency_analysis(limit=recent_draws)
        
        # Include all numbers from 1-37
        all_numbers = {i: 0 for i in range(1, 38)}
        all_numbers.update(freq)
        
        sorted_freq = sorted(all_numbers.items(), key=lambda x: x[1])
        return [num for num, _ in sorted_freq[:top_n]]
    
    def get_overdue_numbers(self, top_n: int = 10) -> List[Tuple[int, int]]:
        """Get numbers that haven't appeared in a while (last 4 years only)."""
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
        
        # Set numbers never appeared to max
        for num in last_appearance:
            if last_appearance[num] == 0:
                last_appearance[num] = len(results)
        
        sorted_overdue = sorted(last_appearance.items(), key=lambda x: x[1], reverse=True)
        return sorted_overdue[:top_n]
    
    def predict_frequency_based(self) -> Tuple[List[int], int]:
        """Predict using frequency analysis (hot numbers)."""
        hot_numbers = self.get_hot_numbers(top_n=15, recent_draws=100)
        
        # Select 6 numbers from hot numbers with some randomness
        if len(hot_numbers) >= 6:
            numbers = sorted(random.sample(hot_numbers, 6))
        else:
            numbers = hot_numbers + random.sample(
                [i for i in range(1, 38) if i not in hot_numbers],
                6 - len(hot_numbers)
            )
            numbers = sorted(numbers)
        
        # Predict strong number
        strong_freq = self.strong_number_frequency(limit=100)
        strong_number = max(strong_freq.items(), key=lambda x: x[1])[0]
        
        return numbers, strong_number
    
    def predict_balanced(self) -> Tuple[List[int], int]:
        """Predict using a balanced approach (mix of hot and cold numbers)."""
        hot_numbers = self.get_hot_numbers(top_n=10, recent_draws=50)
        cold_numbers = self.get_cold_numbers(top_n=10, recent_draws=50)
        
        # Select 3 hot and 3 cold numbers
        selected = []
        if len(hot_numbers) >= 3:
            selected.extend(random.sample(hot_numbers, 3))
        else:
            selected.extend(hot_numbers)
        
        if len(cold_numbers) >= 3:
            selected.extend(random.sample(cold_numbers, 3))
        else:
            selected.extend(cold_numbers)
        
        # Fill up to 6 if needed
        while len(selected) < 6:
            num = random.randint(1, 37)
            if num not in selected:
                selected.append(num)
        
        numbers = sorted(selected[:6])
        
        # Random strong number from frequent ones
        strong_freq = self.strong_number_frequency()
        top_strong = sorted(strong_freq.items(), key=lambda x: x[1], reverse=True)[:3]
        strong_number = random.choice([num for num, _ in top_strong])
        
        return numbers, strong_number
    
    def predict_overdue(self) -> Tuple[List[int], int]:
        """Predict using overdue numbers (numbers that haven't appeared recently)."""
        overdue = self.get_overdue_numbers(top_n=12)
        overdue_numbers = [num for num, _ in overdue]
        
        # Select 6 numbers from overdue with some randomness
        if len(overdue_numbers) >= 6:
            numbers = sorted(random.sample(overdue_numbers, 6))
        else:
            numbers = overdue_numbers + random.sample(
                [i for i in range(1, 38) if i not in overdue_numbers],
                6 - len(overdue_numbers)
            )
            numbers = sorted(numbers[:6])
        
        # Strong number - use less frequent ones
        strong_freq = self.strong_number_frequency()
        strong_number = min(strong_freq.items(), key=lambda x: x[1])[0]
        
        return numbers, strong_number
    
    def predict_pattern_based(self) -> Tuple[List[int], int]:
        """Predict using pattern analysis (analyze recent patterns)."""
        recent_draws = self.get_all_numbers(limit=10)
        
        # Analyze patterns: even/odd distribution, high/low distribution
        numbers = []
        
        # Aim for balanced even/odd (typically 3-3 or 4-2)
        even_count = random.choice([2, 3, 4])
        odd_count = 6 - even_count
        
        # Aim for balanced high/low (1-18 vs 19-37)
        low_count = random.choice([2, 3, 4])
        high_count = 6 - low_count
        
        # Generate numbers based on these constraints
        available_numbers = list(range(1, 38))
        random.shuffle(available_numbers)
        
        for num in available_numbers:
            if len(numbers) >= 6:
                break
            
            is_even = num % 2 == 0
            is_low = num <= 18
            
            if is_even and even_count > 0:
                numbers.append(num)
                even_count -= 1
            elif not is_even and odd_count > 0:
                numbers.append(num)
                odd_count -= 1
        
        # Fill remaining if needed
        while len(numbers) < 6:
            num = random.randint(1, 37)
            if num not in numbers:
                numbers.append(num)
        
        numbers = sorted(numbers[:6])
        
        # Strong number from recent patterns
        recent_strong = self.get_all_strong_numbers(limit=10)
        strong_number = random.choice(recent_strong) if recent_strong else random.randint(1, 7)
        
        return numbers, strong_number
    
    def predict_statistical_average(self) -> Tuple[List[int], int]:
        """Predict using statistical average approach."""
        freq = self.frequency_analysis()
        
        # Calculate average frequency
        avg_freq = sum(freq.values()) / len(freq)
        
        # Select numbers close to average frequency
        candidates = []
        for num, count in freq.items():
            if abs(count - avg_freq) <= avg_freq * 0.3:  # Within 30% of average
                candidates.append(num)
        
        if len(candidates) >= 6:
            numbers = sorted(random.sample(candidates, 6))
        else:
            numbers = candidates + random.sample(
                [i for i in range(1, 38) if i not in candidates],
                6 - len(candidates)
            )
            numbers = sorted(numbers[:6])
        
        # Strong number - middle frequency
        strong_freq = self.strong_number_frequency()
        strong_avg = sum(strong_freq.values()) / len(strong_freq)
        strong_candidates = [num for num, count in strong_freq.items() 
                           if abs(count - strong_avg) <= strong_avg * 0.3]
        strong_number = random.choice(strong_candidates) if strong_candidates else random.randint(1, 7)
        
        return numbers, strong_number
    
    def predict_recent_trends(self) -> Tuple[List[int], int]:
        """Predict based on very recent draws (last 5-10 draws only)."""
        recent_draws = self.get_all_numbers(limit=10)
        flat_numbers = [num for draw in recent_draws for num in draw]
        recent_freq = Counter(flat_numbers)
        
        # Get top trending numbers
        top_recent = sorted(recent_freq.items(), key=lambda x: x[1], reverse=True)[:12]
        trending = [num for num, _ in top_recent]
        
        if len(trending) >= 6:
            numbers = sorted(random.sample(trending, 6))
        else:
            numbers = trending + random.sample(
                [i for i in range(1, 38) if i not in trending],
                6 - len(trending)
            )
            numbers = sorted(numbers[:6])
        
        # Recent strong numbers
        recent_strong = self.get_all_strong_numbers(limit=10)
        strong_freq = Counter(recent_strong)
        strong_number = strong_freq.most_common(1)[0][0] if strong_freq else random.randint(1, 7)
        
        return numbers, strong_number
    
    def predict_number_pairs(self) -> Tuple[List[int], int]:
        """Predict using common number pair analysis."""
        recent_draws = self.get_all_numbers(limit=100)
        
        # Find most common pairs
        pairs = []
        for draw in recent_draws:
            for i in range(len(draw)):
                for j in range(i + 1, len(draw)):
                    pairs.append(tuple(sorted([draw[i], draw[j]])))
        
        pair_freq = Counter(pairs)
        top_pairs = pair_freq.most_common(10)
        
        # Build numbers from top pairs
        numbers = []
        for pair, _ in top_pairs:
            for num in pair:
                if num not in numbers:
                    numbers.append(num)
                if len(numbers) >= 6:
                    break
            if len(numbers) >= 6:
                break
        
        # Fill up if needed
        while len(numbers) < 6:
            num = random.randint(1, 37)
            if num not in numbers:
                numbers.append(num)
        
        numbers = sorted(numbers[:6])
        
        # Strong number from pairs strategy
        strong_freq = self.strong_number_frequency(limit=100)
        strong_number = max(strong_freq.items(), key=lambda x: x[1])[0]
        
        return numbers, strong_number
    
    def predict_sum_based(self) -> Tuple[List[int], int]:
        """Predict targeting the average sum of winning numbers."""
        recent_draws = self.get_all_numbers(limit=100)
        
        # Calculate average sum
        sums = [sum(draw) for draw in recent_draws]
        avg_sum = sum(sums) / len(sums)
        target_sum = int(avg_sum)
        
        # Generate numbers targeting the average sum (±10%)
        min_sum = target_sum - int(target_sum * 0.1)
        max_sum = target_sum + int(target_sum * 0.1)
        
        # Try to generate numbers with sum in range
        attempts = 0
        while attempts < 100:
            numbers = sorted(random.sample(range(1, 38), 6))
            current_sum = sum(numbers)
            if min_sum <= current_sum <= max_sum:
                break
            attempts += 1
        
        # Strong number - use most common
        strong_freq = self.strong_number_frequency(limit=100)
        strong_number = max(strong_freq.items(), key=lambda x: x[1])[0]
        
        return numbers, strong_number
    
    def predict_odd_even_balanced(self) -> Tuple[List[int], int]:
        """Predict with balanced odd/even distribution (3-3 split)."""
        # Analyze recent odd/even patterns
        recent_draws = self.get_all_numbers(limit=50)
        odd_freq = Counter()
        even_freq = Counter()
        
        for draw in recent_draws:
            for num in draw:
                if num % 2 == 0:
                    even_freq[num] += 1
                else:
                    odd_freq[num] += 1
        
        # Get top odds and evens
        top_odds = [num for num, _ in odd_freq.most_common(10)]
        top_evens = [num for num, _ in even_freq.most_common(10)]
        
        # Select 3 odds and 3 evens
        numbers = []
        if len(top_odds) >= 3:
            numbers.extend(random.sample(top_odds, 3))
        else:
            numbers.extend(top_odds)
            odds = [i for i in range(1, 38, 2) if i not in numbers]
            numbers.extend(random.sample(odds, 3 - len(top_odds)))
        
        if len(top_evens) >= 3:
            numbers.extend(random.sample(top_evens, 3))
        else:
            numbers.extend(top_evens)
            evens = [i for i in range(2, 38, 2) if i not in numbers]
            numbers.extend(random.sample(evens, 3 - len(top_evens)))
        
        numbers = sorted(numbers[:6])
        
        # Balanced strong number
        strong_freq = self.strong_number_frequency(limit=50)
        strong_number = random.choice(list(strong_freq.keys()))
        
        return numbers, strong_number
    
    def predict_spread_distribution(self) -> Tuple[List[int], int]:
        """Predict with even spread across number range (no clustering)."""
        # Divide range 1-37 into 6 segments
        segment_size = 37 / 6
        numbers = []
        
        for i in range(6):
            start = int(i * segment_size) + 1
            end = int((i + 1) * segment_size)
            
            # Get frequency for this segment
            freq = self.frequency_analysis(limit=100)
            segment_nums = {k: v for k, v in freq.items() if start <= k <= end}
            
            if segment_nums:
                # Pick most common from this segment
                num = max(segment_nums.items(), key=lambda x: x[1])[0]
            else:
                # Random from segment if no data
                num = random.randint(start, min(end, 37))
            
            numbers.append(num)
        
        numbers = sorted(numbers)
        
        # Strong number - avoid most common
        strong_freq = self.strong_number_frequency(limit=100)
        mid_strong = sorted(strong_freq.items(), key=lambda x: x[1])[len(strong_freq)//2]
        strong_number = mid_strong[0]
        
        return numbers, strong_number
    
    def _set_variety_seed(self, variety: int, strategy_name: str):
        """Set random seed based on variety level.
        
        variety: 0-100
            0 = Fully deterministic (same results every time)
            100 = Fully random (different results every time)
        """
        if variety >= 100:
            # Full randomness - don't set seed
            return
        
        # Create a base seed from current data state
        self.cursor.execute(f"""
            SELECT COUNT(*), MAX(draw_number) FROM lottery_results 
            WHERE {self.CURRENT_SYSTEM_FILTER} AND {self.DATE_FILTER}
        """)
        count, max_draw = self.cursor.fetchone()
        
        # Create deterministic seed from data + strategy
        seed_string = f"{count}_{max_draw}_{strategy_name}"
        seed_hash = int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)
        
        if variety == 0:
            # Fully deterministic
            random.seed(seed_hash)
        else:
            # Partial variety: mix deterministic seed with some randomness
            # Higher variety = more random component
            random_component = random.randint(0, variety)
            mixed_seed = seed_hash + random_component
            random.seed(mixed_seed)
    
    def generate_predictions(self, num_predictions: int = 5, variety: int = 100) -> List[Dict]:
        """Generate multiple predictions using different strategies.
        
        Args:
            num_predictions: Number of predictions to generate (1-10)
            variety: 0-100, controls randomness
                0 = Same predictions every time (deterministic)
                50 = Some variety
                100 = Full randomness (default, current behavior)
        """
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
            
            # Set seed based on variety level
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
        """Get comprehensive statistics about the lottery data (last 4 years only)."""
        freq = self.frequency_analysis()
        strong_freq = self.strong_number_frequency()
        hot_numbers = self.get_hot_numbers(top_n=6, recent_draws=50)
        cold_numbers = self.get_cold_numbers(top_n=6, recent_draws=50)
        overdue = self.get_overdue_numbers(top_n=6)
        
        # Get total draws (last 4 years, current system only)
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
            "most_common_number": max(freq.items(), key=lambda x: x[1]),
            "least_common_number": min(freq.items(), key=lambda x: x[1]),
            "most_common_strong": max(strong_freq.items(), key=lambda x: x[1]),
            "least_common_strong": min(strong_freq.items(), key=lambda x: x[1]),
        }


if __name__ == "__main__":
    predictor = LotteryPredictor()
    predictor.connect()
    
    print("Generating lottery predictions...\n")
    predictions = predictor.generate_predictions(5)
    
    for pred in predictions:
        print(f"Prediction #{pred['prediction_number']} - {pred['strategy']}")
        print(f"  Numbers: {pred['numbers']}")
        print(f"  Strong Number: {pred['strong_number']}")
        print()
    
    predictor.close()

