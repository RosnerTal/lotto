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
        """Fetch and filter draws from Firestore (last 4 years)."""
        global _predictor_cache, _predictor_cache_time
        
        if _predictor_cache is not None and (time.time() - _predictor_cache_time) < PREDICTOR_CACHE_TTL:
            return _predictor_cache

        # Calculate 4 years ago
        four_years_ago = (datetime.now() - timedelta(days=4*365)).strftime("%Y-%m-%d")
        
        # Firestore query
        docs = self.db.collection('draws')\
            .where('draw_date', '>=', four_years_ago)\
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

    # ... Prediction strategies stay the same as they use the helper methods above ...
    def predict_frequency_based(self) -> Tuple[List[int], int]:
        hot_numbers = self.get_hot_numbers(top_n=15, recent_draws=100)
        if len(hot_numbers) >= 6:
            numbers = sorted(random.sample(hot_numbers, 6))
        else:
            numbers = sorted(hot_numbers + random.sample([i for i in range(1, 38) if i not in hot_numbers], 6 - len(hot_numbers)))
        strong_freq = self.strong_number_frequency(limit=100)
        strong_number = max(strong_freq.items(), key=lambda x: x[1])[0] if strong_freq else random.randint(1, 7)
        return numbers, strong_number

    def predict_balanced(self) -> Tuple[List[int], int]:
        hot_numbers = self.get_hot_numbers(top_n=10, recent_draws=50)
        cold_numbers = self.get_cold_numbers(top_n=10, recent_draws=50)
        selected = []
        selected.extend(random.sample(hot_numbers, min(len(hot_numbers), 3)))
        selected.extend(random.sample(cold_numbers, min(len(cold_numbers), 3)))
        while len(selected) < 6:
            num = random.randint(1, 37)
            if num not in selected: selected.append(num)
        strong_freq = self.strong_number_frequency()
        top_strong = sorted(strong_freq.items(), key=lambda x: x[1], reverse=True)[:3]
        strong_number = random.choice([num for num, _ in top_strong]) if top_strong else random.randint(1, 7)
        return sorted(selected[:6]), strong_number

    def predict_overdue(self) -> Tuple[List[int], int]:
        overdue = self.get_overdue_numbers(top_n=12)
        overdue_numbers = [num for num, _ in overdue]
        numbers = sorted(random.sample(overdue_numbers, 6)) if len(overdue_numbers) >= 6 else sorted(overdue_numbers + random.sample([i for i in range(1, 38) if i not in overdue_numbers], 6 - len(overdue_numbers))[:6])
        strong_freq = self.strong_number_frequency()
        strong_number = min(strong_freq.items(), key=lambda x: x[1])[0] if strong_freq else random.randint(1, 7)
        return numbers, strong_number

    def predict_pattern_based(self) -> Tuple[List[int], int]:
        numbers = []
        even_count = random.choice([2, 3, 4])
        odd_count = 6 - even_count
        available = list(range(1, 38))
        random.shuffle(available)
        for num in available:
            if len(numbers) >= 6: break
            if (num % 2 == 0 and even_count > 0):
                numbers.append(num)
                even_count -= 1
            elif (num % 2 != 0 and odd_count > 0):
                numbers.append(num)
                odd_count -= 1
        while len(numbers) < 6:
            num = random.randint(1, 37)
            if num not in numbers: numbers.append(num)
        recent_strong = self.get_all_strong_numbers(limit=10)
        strong_number = random.choice(recent_strong) if recent_strong else random.randint(1, 7)
        return sorted(numbers[:6]), strong_number

    def predict_statistical_average(self) -> Tuple[List[int], int]:
        freq = self.frequency_analysis()
        if not freq: return sorted(random.sample(range(1,38), 6)), random.randint(1,7)
        avg_freq = sum(freq.values()) / len(freq)
        candidates = [num for num, count in freq.items() if abs(count - avg_freq) <= avg_freq * 0.3]
        numbers = sorted(random.sample(candidates, 6)) if len(candidates) >= 6 else sorted(candidates + random.sample([i for i in range(1,38) if i not in candidates], 6-len(candidates))[:6])
        strong_freq = self.strong_number_frequency()
        strong_avg = sum(strong_freq.values()) / len(strong_freq) if strong_freq else 0
        strong_candidates = [num for num, count in strong_freq.items() if abs(count - strong_avg) <= strong_avg * 0.3]
        strong_number = random.choice(strong_candidates) if strong_candidates else random.randint(1, 7)
        return numbers, strong_number

    def predict_recent_trends(self) -> Tuple[List[int], int]:
        recent_draws = self.get_all_numbers(limit=10)
        flat = [num for draw in recent_draws for num in draw]
        recent_freq = Counter(flat)
        trending = [num for num, _ in recent_freq.most_common(12)]
        numbers = sorted(random.sample(trending, 6)) if len(trending) >= 6 else sorted(trending + random.sample([i for i in range(1,38) if i not in trending], 6-len(trending))[:6])
        recent_strong = self.get_all_strong_numbers(limit=10)
        strong_number = Counter(recent_strong).most_common(1)[0][0] if recent_strong else random.randint(1, 7)
        return numbers, strong_number

    def predict_number_pairs(self) -> Tuple[List[int], int]:
        recent_draws = self.get_all_numbers(limit=100)
        pairs = []
        for draw in recent_draws:
            for i in range(len(draw)):
                for j in range(i + 1, len(draw)):
                    pairs.append(tuple(sorted([draw[i], draw[j]])))
        top_pairs = Counter(pairs).most_common(10)
        numbers = []
        for pair, _ in top_pairs:
            for num in pair:
                if num not in numbers: numbers.append(num)
                if len(numbers) >= 6: break
            if len(numbers) >= 6: break
        while len(numbers) < 6:
            num = random.randint(1, 37)
            if num not in numbers: numbers.append(num)
        strong_freq = self.strong_number_frequency(limit=100)
        strong_number = max(strong_freq.items(), key=lambda x: x[1])[0] if strong_freq else random.randint(1, 7)
        return sorted(numbers[:6]), strong_number

    def predict_sum_based(self) -> Tuple[List[int], int]:
        recent_draws = self.get_all_numbers(limit=100)
        if not recent_draws: return sorted(random.sample(range(1,38), 6)), random.randint(1,7)
        avg_sum = sum(sum(draw) for draw in recent_draws) / len(recent_draws)
        min_sum, max_sum = int(avg_sum * 0.9), int(avg_sum * 1.1)
        for _ in range(100):
            numbers = sorted(random.sample(range(1, 38), 6))
            if min_sum <= sum(numbers) <= max_sum: break
        strong_freq = self.strong_number_frequency(limit=100)
        strong_number = max(strong_freq.items(), key=lambda x: x[1])[0] if strong_freq else random.randint(1, 7)
        return numbers, strong_number

    def predict_odd_even_balanced(self) -> Tuple[List[int], int]:
        recent_draws = self.get_all_numbers(limit=50)
        odd_f, even_f = Counter(), Counter()
        for draw in recent_draws:
            for n in draw:
                if n % 2 == 0: even_f[n] += 1
                else: odd_f[n] += 1
        numbers = random.sample([n for n, _ in odd_f.most_common(10)], 3) + random.sample([n for n, _ in even_f.most_common(10)], 3)
        while len(numbers) < 6:
            n = random.randint(1, 37)
            if n not in numbers: numbers.append(n)
        return sorted(numbers[:6]), random.randint(1, 7)

    def predict_spread_distribution(self) -> Tuple[List[int], int]:
        segment_size = 37 / 6
        numbers = []
        freq = self.frequency_analysis(limit=100)
        for i in range(6):
            start, end = int(i * segment_size) + 1, int((i + 1) * segment_size)
            seg_nums = {k: v for k, v in freq.items() if start <= k <= end}
            numbers.append(max(seg_nums.items(), key=lambda x: x[1])[0] if seg_nums else random.randint(start, min(end, 37)))
        return sorted(numbers), random.randint(1, 7)

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
