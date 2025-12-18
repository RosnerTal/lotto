"""
Scraper to fetch latest lottery results from lottosheli.co.il
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict
import re


def fetch_latest_result() -> Optional[Dict]:
    """
    Fetch the latest lottery result from lottosheli.co.il
    
    Returns:
        Dict with keys: draw_number, date, numbers (list of 6), strong_number
        None if fetch fails
    """
    try:
        url = "https://lottosheli.co.il/results/lotto"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the dropdown with draw numbers (first option is the latest)
        select = soup.find('select')
        if not select:
            return None
        
        # Get the first option (latest draw)
        first_option = select.find('option')
        if not first_option:
            return None
        
        option_text = first_option.text.strip()
        
        # Parse: "מספר הגרלה: 3878 תאריך: 16.12.2025"
        draw_match = re.search(r'(\d+).*?(\d{2}\.\d{2}\.\d{4})', option_text)
        if not draw_match:
            return None
        
        draw_number = int(draw_match.group(1))
        date_str = draw_match.group(2)  # DD.MM.YYYY
        
        # Convert date from DD.MM.YYYY to DD/MM/YYYY
        date_formatted = date_str.replace('.', '/')
        
        # Find the lottery balls (numbers displayed on page)
        # Look for divs or spans with the numbers
        numbers = []
        strong_number = None
        
        # Try to find number elements - they're usually in specific classes or containers
        # The structure shows numbers like: 33 28 25 23 5 1 and EXTRA: 2
        number_elements = soup.find_all(string=re.compile(r'^\d+$'))
        
        # Filter to get just the lottery numbers (looking for numbers 1-37)
        for elem in number_elements:
            num_text = elem.strip()
            if num_text.isdigit():
                num = int(num_text)
                if 1 <= num <= 37 and len(numbers) < 6:
                    numbers.append(num)
                elif 1 <= num <= 7 and len(numbers) == 6 and strong_number is None:
                    strong_number = num
        
        # Verify we got all numbers
        if len(numbers) != 6 or strong_number is None:
            return None
        
        return {
            'draw_number': draw_number,
            'date': date_formatted,
            'numbers': numbers,
            'strong_number': strong_number
        }
    
    except Exception as e:
        print(f"Error fetching lottery results: {e}")
        return None


def fetch_draw_from_page(draw_number: int) -> Optional[Dict]:
    """
    Fetch a specific draw result by submitting the form
    
    Args:
        draw_number: The draw number to fetch
    
    Returns:
        Dict with lottery result or None if not found
    """
    try:
        url = "https://lottosheli.co.il/results/lotto"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Create a session to handle the form submission
        session = requests.Session()
        
        # First, get the page to find the form structure
        response = session.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the select element with draw numbers
        select = soup.find('select')
        if not select:
            return None
        
        # Check if the draw number exists in the options
        option = select.find('option', string=lambda s: s and str(draw_number) in s)
        if not option:
            return None
        
        option_text = option.text.strip()
        
        # Parse the option text
        draw_match = re.search(r'(\d+).*?(\d{2}\.\d{2}\.\d{4})', option_text)
        if not draw_match:
            return None
        
        date_str = draw_match.group(2)
        date_formatted = date_str.replace('.', '/')
        
        # Get the page HTML and parse numbers
        # The numbers should be visible in the initial page load for the selected draw
        # For now, we'll return basic info and let the user verify
        # In a full implementation, we'd submit the form and parse the result
        
        # For this version, we'll just return the draw info without numbers
        # This is a placeholder - full implementation would require form submission
        return {
            'draw_number': draw_number,
            'date': date_formatted,
            'numbers': [],  # Would need form submission to get
            'strong_number': None
        }
    
    except Exception as e:
        print(f"Error fetching draw {draw_number}: {e}")
        return None


def fetch_multiple_draws(start_draw: int, end_draw: int) -> list:
    """
    Fetch multiple draws by scraping the page for each draw in the dropdown
    
    Args:
        start_draw: First draw number to fetch (inclusive)
        end_draw: Last draw number to fetch (inclusive)
    
    Returns:
        List of draw dictionaries
    """
    results = []
    
    try:
        url = "https://lottosheli.co.il/results/lotto"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all options in the select dropdown
        select = soup.find('select')
        if not select:
            return results
        
        options = select.find_all('option')
        
        # Parse each option that's in our range
        for option in options:
            option_text = option.text.strip()
            draw_match = re.search(r'(\d+).*?(\d{2}\.\d{2}\.\d{4})', option_text)
            
            if draw_match:
                draw_num = int(draw_match.group(1))
                
                # Only process draws in our range
                if start_draw <= draw_num <= end_draw:
                    date_str = draw_match.group(2)
                    date_formatted = date_str.replace('.', '/')
                    
                    # Since all draws are in the dropdown but only the latest shows numbers,
                    # we need to note that we can only reliably get the latest draw
                    results.append({
                        'draw_number': draw_num,
                        'date': date_formatted,
                        'needs_manual_entry': True
                    })
        
        return sorted(results, key=lambda x: x['draw_number'])
    
    except Exception as e:
        print(f"Error fetching multiple draws: {e}")
        return results


if __name__ == "__main__":
    # Test the scraper
    result = fetch_latest_result()
    if result:
        print("Latest Lottery Result:")
        print(f"  Draw #: {result['draw_number']}")
        print(f"  Date: {result['date']}")
        print(f"  Numbers: {result['numbers']}")
        print(f"  Strong Number: {result['strong_number']}")
    else:
        print("Failed to fetch results")

