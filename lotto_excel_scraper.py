"""
Scraper using lottosheli.co.il Excel export API
This can fetch multiple draws at once!
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import io


def fetch_draws_excel(from_date: str = None, to_date: str = None, from_draw: int = None, to_draw: int = None) -> List[Dict]:
    """
    Fetch lottery draws using the Excel export API
    
    Args:
        from_date: Start date in DD/MM/YYYY format (optional)
        to_date: End date in DD/MM/YYYY format (optional)
        from_draw: Starting draw number (optional)
        to_draw: Ending draw number (optional)
    
    Returns:
        List of draw dictionaries with draw_number, date, numbers, strong_number
    """
    try:
        # If no dates provided, use last 3 months
        if not from_date:
            from_dt = datetime.now() - timedelta(days=90)
            from_date = from_dt.strftime("%d/%m/%Y")
        
        if not to_date:
            to_dt = datetime.now()
            to_date = to_dt.strftime("%d/%m/%Y")
        
        # Convert dates to Unix timestamps
        from_dt = datetime.strptime(from_date, "%d/%m/%Y")
        to_dt = datetime.strptime(to_date, "%d/%m/%Y")
        
        from_timestamp = int(from_dt.timestamp())
        to_timestamp = int(to_dt.timestamp())
        
        # Build URL
        base_url = "https://lottosheli.co.il/results/report/export"
        url = f"{base_url}?game=lotto&from={from_timestamp}&to={to_timestamp}"
        
        print(f"Fetching draws from {from_date} to {to_date}...")
        print(f"URL: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Parse Excel file
        df = pd.read_excel(io.BytesIO(response.content))
        
        print(f"Received {len(df)} rows")
        print(f"Columns: {list(df.columns)}")
        
        # Parse the data
        results = []
        
        for idx, row in df.iterrows():
            try:
                # Extract draw number and date
                draw_number = int(row.iloc[0])  # First column
                date_val = row.iloc[1]  # Second column
                
                # Parse date
                if isinstance(date_val, str):
                    date_str = date_val.replace('.', '/')
                else:
                    date_str = date_val.strftime("%d/%m/%Y")
                
                # Extract numbers - they're in column 2 as comma-separated string
                numbers_str = str(row.iloc[2])  # Third column: "1,5,23,25,28,33"
                numbers = [int(n.strip()) for n in numbers_str.split(',')]
                
                # Validate we got 6 numbers
                if len(numbers) != 6:
                    print(f"  Warning: Draw {draw_number} has {len(numbers)} numbers, skipping")
                    continue
                
                # Extract strong number (column 3)
                strong_number = int(row.iloc[3])
                
                # Filter by draw number range if specified
                if from_draw and draw_number < from_draw:
                    continue
                if to_draw and draw_number > to_draw:
                    continue
                
                results.append({
                    'draw_number': draw_number,
                    'date': date_str,
                    'numbers': numbers,
                    'strong_number': strong_number
                })
                
            except Exception as e:
                print(f"Error parsing row {idx}: {e}")
                continue
        
        print(f"Successfully parsed {len(results)} draws")
        return results
        
    except Exception as e:
        print(f"Error fetching Excel: {e}")
        return []


def fetch_missing_draws_excel(from_draw: int, to_draw: int) -> List[Dict]:
    """
    Fetch specific range of draws using Excel export
    
    Args:
        from_draw: Starting draw number
        to_draw: Ending draw number
    
    Returns:
        List of draw dictionaries
    """
    # Calculate approximate date range (lottery is ~2-3 times per week)
    # So 10 draws = ~4-5 weeks
    days_back = (to_draw - from_draw + 1) * 4  # Estimate 4 days per draw
    days_back = max(days_back, 90)  # At least 3 months
    
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%d/%m/%Y")
    to_date = datetime.now().strftime("%d/%m/%Y")
    
    results = fetch_draws_excel(from_date=from_date, to_date=to_date, 
                                from_draw=from_draw, to_draw=to_draw)
    
    return results


if __name__ == "__main__":
    # Test fetching recent draws
    print("Testing Excel scraper...")
    results = fetch_draws_excel()
    
    if results:
        print(f"\nFetched {len(results)} draws")
        print("\nLatest 3 draws:")
        for r in results[:3]:
            print(f"  Draw #{r['draw_number']} ({r['date']}): {r['numbers']} + {r['strong_number']}")
    else:
        print("Failed to fetch")

