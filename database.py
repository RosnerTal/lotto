import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from typing import List, Tuple, Optional
import os

class LotteryDatabase:
    def __init__(self):
        self._initialized = False
        self.db = None

    def connect(self):
        """Connect to Firestore."""
        if not self._initialized:
            # Check if already initialized (to avoid error)
            if not firebase_admin._apps:
                service_account = 'service-account.json'
                if os.path.exists(service_account):
                    cred = credentials.Certificate(service_account)
                    firebase_admin.initialize_app(cred)
                else:
                    # Fallback for Cloud Run environment
                    firebase_admin.initialize_app()
            
            self.db = firestore.client()
            self._initialized = True
    
    def close(self):
        """No explicit close needed for Firestore client."""
        pass
    
    def add_result(self, draw_number: int, draw_date: str, 
                   numbers: List[int], strong_number: int) -> bool:
        """Add a new lottery result to Firestore."""
        try:
            if len(numbers) != 6:
                raise ValueError("Must provide exactly 6 numbers")
            
            # Standardize date format to YYYY-MM-DD
            if '/' in draw_date:
                date_obj = datetime.strptime(draw_date, "%d/%m/%Y")
                draw_date = date_obj.strftime("%Y-%m-%d")
            
            doc_ref = self.db.collection('draws').document(str(draw_number))
            doc_ref.set({
                'draw_number': draw_number,
                'draw_date': draw_date,
                'numbers': numbers,
                'strong_number': strong_number,
                'created_at': firestore.SERVER_TIMESTAMP
            })
            return True
        except Exception as e:
            print(f"Error adding result: {e}")
            return False
    
    def get_all_results(self) -> List[Tuple]:
        """Get all lottery results ordered by date descending."""
        # Note: Firestore might need an index for this if not already created
        docs = self.db.collection('draws').order_by('draw_date', direction=firestore.Query.DESCENDING).stream()
        results = []
        for doc in docs:
            d = doc.to_dict()
            nums = d.get('numbers', [0,0,0,0,0,0])
            results.append((
                d['draw_number'],
                d['draw_date'],
                nums[0], nums[1], nums[2], nums[3], nums[4], nums[5],
                d['strong_number']
            ))
        return results
    
    def get_latest_results(self, limit: int = 10) -> List[Tuple]:
        """Get the latest N lottery results."""
        docs = self.db.collection('draws').order_by('draw_date', direction=firestore.Query.DESCENDING).limit(limit).stream()
        results = []
        for doc in docs:
            d = doc.to_dict()
            nums = d.get('numbers', [0,0,0,0,0,0])
            results.append((
                d['draw_number'],
                d['draw_date'],
                nums[0], nums[1], nums[2], nums[3], nums[4], nums[5],
                d['strong_number']
            ))
        return results
    
    def get_results_count(self) -> int:
        """Get total number of results (Approximate or via aggregation)."""
        # For simplicity in migration, use aggregation query if available or just count stream
        # Better: use the new count() aggregation in Firestore
        query = self.db.collection('draws').count()
        snapshot = query.get()
        return snapshot[0][0].value
    
    def get_latest_draw_number(self) -> Optional[int]:
        """Get the latest draw number in the database."""
        docs = self.db.collection('draws').order_by('draw_date', direction=firestore.Query.DESCENDING).limit(1).stream()
        for doc in docs:
            return doc.to_dict()['draw_number']
        return None

# Keep the same interface as before
def initialize_database():
    """Initialization is handled lazily in Firestore."""
    db = LotteryDatabase()
    db.connect()
    print("Firestore connection verified.")
    return 0, 0
