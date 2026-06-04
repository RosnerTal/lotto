import firebase_admin
from firebase_admin import credentials, firestore
from collections import Counter
from typing import List, Tuple, Dict
import random
import hashlib
from datetime import datetime, timedelta
import os
import time

_predictor_cache = None
_predictor_cache_time = 0
PREDICTOR_CACHE_TTL = 3600  # 1 hour

class LotteryPredictor:
    def __init__(self):
        self.db = None
        self._all_draws = None  # Cache for current session
        self.current_variety = 100

    def connect(self):
        """Connect to Firestore."""
        if not firebase_admin._apps:
            service_account = 'service-account.json'
            if os.path.exists(service_account):
                cred = credentials.Certificate(service_account)
                firebase_admin.initialize_app(cred)
            else:
                firebase_admin.initialize_app()
        
        self.db = firestore.client()

    def close(self):
        pass

    def _get_filtered_draws(self) -> List[Dict]:
        """Fetch and filter draws from Firestore."""
        global _predictor_cache, _predictor_cache_time
        
        if _predictor_cache is not None and (time.time() - _predictor_cache_time) < PREDICTOR_CACHE_TTL:
            return _predictor_cache
        
        # Firestore query - get all draws (old format draws were already removed from the database)
        docs = self.db.collection('draws')\
            .order_by('draw_date', direction=firestore.Query.DESCENDING)\
            .stream()
        
        draws = []
        for doc in docs:
            d = doc.to_dict()
            # Basic validation for "current system"
            if d.get('strong_number', 0) <= 7 and all(1 <= n <= 37 for n in d.get('numbers', [])):
                draws.append(d)
        
        _predictor_cache = draws
        _predictor_cache_time = time.time()
        return draws

    def get_all_numbers(self, limit: int = None) -> List[List[int]]:
        draws = self._get_filtered_draws()
        if limit:
            draws = draws[:limit]
        return [d['numbers'] for d in draws]

    def get_all_strong_numbers(self, limit: int = None) -> List[int]:
        draws = self._get_filtered_draws()
        if limit:
            draws = draws[:limit]
        return [d['strong_number'] for d in draws]

    def frequency_analysis(self, limit: int = None) -> Dict[int, int]:
        all_numbers = self.get_all_numbers(limit)
        flat_numbers = [num for draw in all_numbers for num in draw]
        return dict(Counter(flat_numbers))

    def strong_number_frequency(self, limit: int = None) -> Dict[int, int]:
        strong_numbers = self.get_all_strong_numbers(limit)
        return dict(Counter(strong_numbers))

    def get_hot_numbers(self, top_n: int = 10, recent_draws: int = 50) -> List[int]:
        freq = self.frequency_analysis(limit=recent_draws)
        sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [num for num, _ in sorted_freq[:top_n]]

    def get_cold_numbers(self, top_n: int = 10, recent_draws: int = 50) -> List[int]:
        freq = self.frequency_analysis(limit=recent_draws)
        all_numbers = {i: 0 for i in range(1, 38)}
        all_numbers.update(freq)
        sorted_freq = sorted(all_numbers.items(), key=lambda x: x[1])
        return [num for num, _ in sorted_freq[:top_n]]

    def get_overdue_numbers(self, top_n: int = 10) -> List[Tuple[int, int]]:
        draws = self._get_filtered_draws()
        last_appearance = {i: 0 for i in range(1, 38)}
        
        for idx, d in enumerate(draws):
            for num in d['numbers']:
                if num in last_appearance and last_appearance[num] == 0:
                    last_appearance[num] = idx
        
        for num in last_appearance:
            if last_appearance[num] == 0:
                last_appearance[num] = len(draws)
        
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
        draws = self._get_filtered_draws()
        prev_numbers = draws[0]['numbers'] if draws else []
        
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
        last_seen = {}
        for idx, d in enumerate(draws):
            sn = d['strong_number']
            if sn not in last_seen:
                last_seen[sn] = idx
        for i in range(1, 8):
            if i not in last_seen:
                last_seen[i] = len(draws)
                
        sorted_overdue_sn = sorted(last_seen.items(), key=lambda x: x[1], reverse=True)
        
        # Pool size scales with variety:
        # variety=0 -> pool size 2 (top 2 overdue)
        # variety=50 -> pool size 4 (top 4 overdue)
        # variety=100 -> pool size 7 (completely random selection from all 1-7)
        pool_size = max(2, min(7, 2 + int(self.current_variety / 20)))
        candidates = [item[0] for item in sorted_overdue_sn[:pool_size]]
        strong_number = random.choice(candidates)
        
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
        if variety >= 100: return
        draws = self._get_filtered_draws()
        count = len(draws)
        max_draw = draws[0]['draw_number'] if draws else 0
        seed_string = f"{count}_{max_draw}_{strategy_name}"
        seed_hash = int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)
        if variety == 0: random.seed(seed_hash)
        else: random.seed(seed_hash + random.randint(0, variety))

    def generate_predictions(self, num_predictions: int = 5, variety: int = 100) -> List[Dict]:
        self.current_variety = variety
        strategies = [
            ("Frequency Based", self.predict_frequency_based),
            ("Balanced", self.predict_balanced),
            ("Overdue Numbers", self.predict_overdue),
            ("Pattern Based", self.predict_pattern_based),
            ("Statistical Average", self.predict_statistical_average),
            ("Recent Trends", self.predict_recent_trends),
            ("Number Pairs", self.predict_number_pairs),
            ("Sum-Based", self.predict_sum_based),
            ("Odd/Even Balanced", self.predict_odd_even_balanced),
            ("Spread Distribution", self.predict_spread_distribution),
        ]
        num_predictions = min(num_predictions, 10)
        predictions = []
        for i in range(num_predictions):
            name, func = strategies[i % len(strategies)]
            self._set_variety_seed(variety, f"{name}_{i}")
            numbers, strong = func()
            predictions.append({"prediction_number": i + 1, "strategy": name, "numbers": numbers, "strong_number": strong})
        return predictions

    def get_statistics(self) -> Dict:
        draws = self._get_filtered_draws()
        freq = self.frequency_analysis()
        strong_f = self.strong_number_frequency()
        return {
            "total_draws": len(draws),
            "frequency_all_time": freq,
            "strong_number_frequency": strong_f,
            "hot_numbers": self.get_hot_numbers(top_n=6, recent_draws=50),
            "cold_numbers": self.get_cold_numbers(top_n=6, recent_draws=50),
            "overdue_numbers": [num for num, _ in self.get_overdue_numbers(top_n=6)],
            "most_common_number": max(freq.items(), key=lambda x: x[1]) if freq else (0,0),
            "least_common_number": min(freq.items(), key=lambda x: x[1]) if freq else (0,0),
            "most_common_strong": max(strong_f.items(), key=lambda x: x[1]) if strong_f else (0,0),
            "least_common_strong": min(strong_f.items(), key=lambda x: x[1]) if strong_f else (0,0),
        }
