"""
Scraper to fetch the latest lottery result from the official pais.co.il
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict
import re

def fetch_latest_result() -> Optional[Dict]:
    """
    Fetch the latest lottery result from pais.co.il
    """
    try:
        url = "https://www.pais.co.il/lotto/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Get draw number
        title_element = soup.find('h3', class_='home_news_title category')
        if not title_element:
            return None
        title_text = title_element.text
        draw_match = re.search(r'\d+', title_text)
        if not draw_match:
            return None
        draw_num = int(draw_match.group())
        
        # 2. Get date
        date_div = title_element.find_next_sibling('div')
        if not date_div:
            return None
        date_text = date_div.text
        
        months = {
            'בינואר': '01', 'בפברואר': '02', 'במרץ': '03', 'באפריל': '04',
            'במאי': '05', 'ביוני': '06', 'ביולי': '07', 'באוגוסט': '08',
            'בספטמבר': '09', 'באוקטובר': '10', 'בנובמבר': '11', 'בדצמבר': '12'
        }
        
        day_match = re.search(r'\s(\d{1,2})\s', date_text)
        year_match = re.search(r'\s(\d{4})\s', date_text)
        
        if not day_match or not year_match:
            return None
            
        day = day_match.group(1).zfill(2)
        year = year_match.group(1)
        
        month = '01'
        for m_name, m_num in months.items():
            if m_name in date_text:
                month = m_num
                break
                
        date_formatted = f'{day}/{month}/{year}'
        
        # 3. Get numbers
        loto_group = soup.find('div', class_='cat_h_data_group loto')
        if not loto_group:
            return None
            
        num_divs = loto_group.find_all('div', class_='loto_info_num')
        numbers = []
        for d in num_divs:
            val = d.text.strip()
            if val.isdigit():
                numbers.append(int(val))
                
        if len(numbers) != 6:
            return None
            
        # 4. Get strong number
        strong_group = soup.find('div', class_='cat_h_data_group strong_num')
        if not strong_group:
            return None
            
        strong_div = strong_group.find('div', class_='loto_info_num strong')
        if not strong_div or not strong_div.text.strip().isdigit():
            return None
            
        strong_number = int(strong_div.text.strip())
        
        return {
            'draw_number': draw_num,
            'date': date_formatted,
            'numbers': sorted(numbers),
            'strong_number': strong_number
        }
        
    except Exception as e:
        print(f"Error fetching lottery results: {e}")
        return None

def fetch_draw_result(draw_number: int = None) -> Optional[Dict]:
    """Fallback - currently only fetches latest from Pais."""
    return fetch_latest_result()

def fetch_multiple_draws(start_draw: int, end_draw: int) -> list:
    """Fallback."""
    return []
