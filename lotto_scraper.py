"""
Scraper to fetch the latest lottery result from the official pais.co.il
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict
import re

def fetch_latest_from_html() -> Optional[Dict]:
    """Fetch latest draw by scraping pais.co.il HTML."""
    try:
        url = "https://www.pais.co.il/lotto/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Try modern layout: div.lotto_past
        past_div = soup.find('div', class_='lotto_past')
        if past_div:
            result_gr = past_div.find('div', class_='past_result_gr')
            if result_gr:
                draw_el = result_gr.find('div', class_='result_num')
                date_gr = result_gr.find('div', class_='result_date_gr')
                date_el = date_gr.find('div', class_='result_num') if date_gr else None
                
                lotto_div = past_div.find('div', class_='past_nums lotto')
                strong_div = past_div.find('div', class_='past_nums strong')
                
                if draw_el and draw_el.text.strip().isdigit() and lotto_div and strong_div:
                    draw_num = int(draw_el.text.strip())
                    date_str = date_el.text.strip() if date_el else ""
                    
                    nums = []
                    for d in lotto_div.find_all('div', class_='lotto_num'):
                        v = d.text.strip()
                        if v.isdigit():
                            nums.append(int(v))
                            
                    strong_el = strong_div.find('div', class_='lotto_num strong')
                    if len(nums) == 6 and strong_el and strong_el.text.strip().isdigit():
                        return {
                            'draw_number': draw_num,
                            'date': date_str,
                            'numbers': sorted(nums),
                            'strong_number': int(strong_el.text.strip())
                        }
        
        # 2. Try legacy layout: home_news_title category
        title_element = soup.find('h3', class_='home_news_title category')
        if title_element:
            title_text = title_element.text
            draw_match = re.search(r'\d+', title_text)
            if draw_match:
                draw_num = int(draw_match.group())
                date_div = title_element.find_next_sibling('div')
                if date_div:
                    date_text = date_div.text
                    months = {
                        'בינואר': '01', 'בפברואר': '02', 'במרץ': '03', 'באפריל': '04',
                        'במאי': '05', 'ביוני': '06', 'ביולי': '07', 'באוגוסט': '08',
                        'בספטמבר': '09', 'באוקטובר': '10', 'בנובמבר': '11', 'בדצמבר': '12'
                    }
                    day_match = re.search(r'\s(\d{1,2})\s', date_text)
                    year_match = re.search(r'\s(\d{4})\s', date_text)
                    if day_match and year_match:
                        day = day_match.group(1).zfill(2)
                        year = year_match.group(1)
                        month = '01'
                        for m_name, m_num in months.items():
                            if m_name in date_text:
                                month = m_num
                                break
                        date_formatted = f'{day}/{month}/{year}'
                        
                        loto_group = soup.find('div', class_='cat_h_data_group loto')
                        if loto_group:
                            numbers = [int(d.text.strip()) for d in loto_group.find_all('div', class_='loto_info_num') if d.text.strip().isdigit()]
                            strong_group = soup.find('div', class_='cat_h_data_group strong_num')
                            if len(numbers) == 6 and strong_group:
                                strong_div = strong_group.find('div', class_='loto_info_num strong')
                                if strong_div and strong_div.text.strip().isdigit():
                                    return {
                                        'draw_number': draw_num,
                                        'date': date_formatted,
                                        'numbers': sorted(numbers),
                                        'strong_number': int(strong_div.text.strip())
                                    }
    except Exception as e:
        print(f"Error fetching lottery results via HTML: {e}")
        
    return None

def fetch_latest_from_csv() -> Optional[Dict]:
    """Fetch latest draw from official Pais CSV."""
    try:
        from lotto_excel_scraper import fetch_draws_excel
        draws = fetch_draws_excel()
        if draws and len(draws) > 0:
            return draws[0]
    except Exception as e:
        print(f"Error fetching lottery results via CSV: {e}")
    return None

def fetch_latest_result() -> Optional[Dict]:
    """
    Fetch the latest lottery result using HTML scraping, falling back to official Pais CSV.
    """
    # Try HTML first
    res = fetch_latest_from_html()
    if res:
        return res
        
    # Fallback to official CSV
    return fetch_latest_from_csv()

def fetch_draw_result(draw_number: int = None) -> Optional[Dict]:
    """Fetch result for a specific draw number."""
    if not draw_number:
        return fetch_latest_result()
    try:
        from lotto_excel_scraper import fetch_missing_draws_excel
        results = fetch_missing_draws_excel(draw_number, draw_number)
        if results and len(results) > 0:
            return results[0]
    except Exception as e:
        print(f"Error fetching draw #{draw_number}: {e}")
    return None

def fetch_multiple_draws(start_draw: int, end_draw: int) -> list:
    """Fetch results for a range of draws."""
    try:
        from lotto_excel_scraper import fetch_missing_draws_excel
        return fetch_missing_draws_excel(start_draw, end_draw)
    except Exception as e:
        print(f"Error fetching multiple draws {start_draw}-{end_draw}: {e}")
        return []
