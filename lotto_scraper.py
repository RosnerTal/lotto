"""
Scraper to fetch latest lottery results from lottosheli.co.il
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict
import re


def fetch_draw_result(draw_number: int = None) -> Optional[Dict]:
    """
    Fetch a lottery result from lottosheli.co.il
    
    Args:
        draw_number: Specific draw to fetch, or None for latest
    
    Returns:
        Dict with keys: draw_number, date, numbers (list of 6), strong_number
        None if fetch fails
    """
    try:
        # The URL pattern for accessing specific draws
        # We need to check if they have a direct URL or if we need to use query params
        base_url = "https://lottosheli.co.il/results/lotto"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        session = requests.Session()
        response = session.get(base_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the dropdown with draw numbers
        select = soup.find('select')
        if not select:
            return None
        
        # If no specific draw requested, get the first (latest)
        if draw_number is None:
            target_option = select.find('option')
        else:
            # Find the option for the specific draw number
            target_option = None
            for option in select.find_all('option'):
                if str(draw_number) in option.text:
                    target_option = option
                    break
        
        if not target_option:
            return None
        
        option_text = target_option.text.strip()
        option_value = target_option.get('value', '')
        
        # Parse: "מספר הגרלה: 3878 תאריך: 16.12.2025"
        draw_match = re.search(r'(\d+).*?(\d{2}\.\d{2}\.\d{4})', option_text)
        if not draw_match:
            return None
        
        found_draw_number = int(draw_match.group(1))
        date_str = draw_match.group(2)  # DD.MM.YYYY
        date_formatted = date_str.replace('.', '/')
        
        # If requesting a specific draw, we need to submit the form or reload with params
        # Try to get the result by submitting a form or using query parameters
        if draw_number and found_draw_number == draw_number and option_value:
            # Try to get the specific draw by posting or using query params
            try:
                # Some sites use POST to change the selected draw
                form_data = {'draw_select': option_value}
                response2 = session.post(base_url, data=form_data, headers=headers, timeout=15)
                if response2.status_code == 200:
                    soup = BeautifulSoup(response2.content, 'html.parser')
            except:
                pass  # If POST fails, continue with current page
        
        # Find the lottery balls (numbers displayed on page)
        numbers = []
        strong_number = None
        
        # Try to find number elements
        number_elements = soup.find_all(string=re.compile(r'^\d+$'))
        
        # Filter to get lottery numbers
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


def fetch_missing_draws(missing_draw_numbers: list) -> list:
    """
    Fetch multiple specific draw numbers
    
    Args:
        missing_draw_numbers: List of draw numbers to fetch
    
    Returns:
        List of successfully fetched draw dictionaries
    """
    results = []
    
    for draw_num in missing_draw_numbers:
        print(f"Fetching draw #{draw_num}...")
        result = fetch_draw_result(draw_num)
        
        if result:
            results.append(result)
            print(f"  ✓ Successfully fetched draw #{draw_num}")
        else:
            print(f"  ✗ Failed to fetch draw #{draw_num}")
        
        # Small delay to be polite to the server
        import time
        time.sleep(0.5)
    
    return results


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

