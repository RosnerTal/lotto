"""
Scraper using lottosheli.co.il Excel export API
This can fetch multiple draws at once!
"""
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import io


def fetch_draws_excel(from_date: str = None, to_date: str = None, from_draw: int = None, to_draw: int = None) -> List[Dict]:
    """
    Fetch lottery draws using the official Pais CSV download link.
    Replaces the broken lottosheli Excel export API.
    
    Args:
        from_date: Start date in DD/MM/YYYY format (optional)
        to_date: End date in DD/MM/YYYY format (optional)
        from_draw: Starting draw number (optional)
        to_draw: Ending draw number (optional)
    
    Returns:
        List of draw dictionaries with draw_number, date, numbers, strong_number
    """
    try:
        url = "https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        print(f"Fetching draws from official Pais CSV...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Decode CSV content using windows-1255 (Hebrew encoding)
        content = response.content.decode('windows-1255')
        
        import csv
        import io
        csv_reader = csv.reader(io.StringIO(content))
        
        # Skip header
        next(csv_reader)
        
        # Date parsers
        from_dt = datetime.strptime(from_date, "%d/%m/%Y") if from_date else None
        to_dt = datetime.strptime(to_date, "%d/%m/%Y") if to_date else None
        
        results = []
        for idx, row in enumerate(csv_reader):
            if not row or len(row) < 9:
                continue
            try:
                draw_number = int(row[0])
                date_str = row[1].strip()
                
                # Filter by draw number range if specified
                if from_draw and draw_number < from_draw:
                    continue
                if to_draw and draw_number > to_draw:
                    continue
                
                # Filter by date range if specified
                if from_dt or to_dt:
                    row_dt = datetime.strptime(date_str, "%d/%m/%Y")
                    if from_dt and row_dt < from_dt:
                        continue
                    if to_dt and row_dt > to_dt:
                        continue
                
                # Parse numbers (columns 2 to 7)
                numbers = [int(row[i]) for i in range(2, 8)]
                
                # Strong number (column 8)
                strong_number = int(row[8])
                
                results.append({
                    'draw_number': draw_number,
                    'date': date_str,
                    'numbers': sorted(numbers),
                    'strong_number': strong_number
                })
                
            except Exception as row_err:
                # Skip invalid rows silently
                continue
                
        print(f"Successfully parsed {len(results)} draws from official Pais CSV")
        return results
        
    except Exception as e:
        print(f"Error fetching official Pais CSV: {e}")
        return []


def fetch_missing_draws_excel(from_draw: int, to_draw: int) -> List[Dict]:
    """
    Fetch specific range of draws using official Pais CSV.
    
    Args:
        from_draw: Starting draw number
        to_draw: Ending draw number
    
    Returns:
        List of draw dictionaries
    """
    # Fetch all draws and filter by draw number range in fetch_draws_excel
    results = fetch_draws_excel(from_draw=from_draw, to_draw=to_draw)
    return results


if __name__ == "__main__":
    # Test fetching recent draws
    print("Testing official Pais CSV scraper...")
    results = fetch_draws_excel()
    
    if results:
        print(f"\nFetched {len(results)} draws")
        print("\nLatest 3 draws:")
        for r in results[:3]:
            print(f"  Draw #{r['draw_number']} ({r['date']}): {r['numbers']} + {r['strong_number']}")
    else:
        print("Failed to fetch")

