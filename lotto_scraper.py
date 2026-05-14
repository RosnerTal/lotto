"""
Scraper to fetch the latest lottery result from lottosheli.co.il
Note: Can only fetch the currently displayed draw due to JavaScript limitations
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict
import re


def fetch_draw_result(draw_number: int = None) -> Optional[Dict]:
    """
    Fetch a lottery result from lottosheli.co.il
    """
    try:
        base_url = "https://lottosheli.co.il/results/lotto"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        session = requests.Session()
        response = session.get(base_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        select = soup.find('select', id='results-options')
        if not select:
            select = soup.find('select')
            
        if not select:
            return None
        
        # Determine which option to use
        if draw_number is None:
            target_option = select.find('option')
        else:
            target_option = None
            for option in select.find_all('option'):
                if str(draw_number) in option.text:
                    target_option = option
                    break
        
        if not target_option:
            return None
        
        option_text = target_option.text.strip()
        option_value = target_option.get('value', '')
        
        draw_match = re.search(r'(\d+).*?(\d{2}\.\d{2}\.\d{4})', option_text)
        if not draw_match:
            return None
        
        found_draw_number = int(draw_match.group(1))
        date_str = draw_match.group(2)  # DD.MM.YYYY
        date_formatted = date_str.replace('.', '/')
        
        # Find the lottery balls
        numbers = []
        strong_number = None
        
        number_elements = soup.find_all(string=re.compile(r'^\d+$'))
        for elem in number_elements:
            num_text = elem.strip()
            if num_text.isdigit():
                num = int(num_text)
                if 1 <= num <= 37 and len(numbers) < 6:
                    numbers.append(num)
                elif 1 <= num <= 7 and len(numbers) == 6 and strong_number is None:
                    strong_number = num
        
        if len(numbers) != 6 or strong_number is None:
            return None
        
        return {
            'draw_number': found_draw_number,
            'date': date_formatted,
            'numbers': numbers,
            'strong_number': strong_number
        }
    
    except Exception as e:
        print(f"Error fetching lottery results: {e}")
        return None


def fetch_latest_result() -> Optional[Dict]:
    """Fetch the latest lottery result."""
    return fetch_draw_result(None)


def fetch_multiple_draws(start_draw: int, end_draw: int) -> list:
    """Fetch multiple draws by parsing dropdown options."""
    results = []
    try:
        url = "https://lottosheli.co.il/results/lotto"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        select = soup.find('select')
        if not select: return results
        
        for option in select.find_all('option'):
            option_text = option.text.strip()
            draw_match = re.search(r'(\d+).*?(\d{2}\.\d{2}\.\d{4})', option_text)
            if draw_match:
                draw_num = int(draw_match.group(1))
                if start_draw <= draw_num <= end_draw:
                    results.append({
                        'draw_number': draw_num,
                        'date': draw_match.group(2).replace('.', '/'),
                        'needs_manual_entry': True
                    })
        return sorted(results, key=lambda x: x['draw_number'])
    except:
        return results

if __name__ == "__main__":
    result = fetch_latest_result()
    print(result)
