import requests
from bs4 import BeautifulSoup
import re

url = "https://www.pais.co.il/lotto/archive.aspx"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

print("Fetching Pais archive page...\n")
response = requests.get(url, headers=headers, timeout=15)

if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Look for form elements
    form = soup.find('form')
    if form:
        print("Form found!")
        print(f"Form action: {form.get('action', 'N/A')}")
        print(f"Form method: {form.get('method', 'N/A')}")
        print()
        
        # Find all input fields
        inputs = form.find_all('input')
        print(f"Input fields: {len(inputs)}")
        for inp in inputs[:10]:  # Show first 10
            print(f"  - {inp.get('name', 'N/A')}: {inp.get('type', 'text')} = {inp.get('value', '')[:50]}")
        print()
        
        # Find select dropdowns
        selects = form.find_all('select')
        print(f"Select dropdowns: {len(selects)}")
        for sel in selects:
            print(f"  - {sel.get('name', 'N/A')}: {len(sel.find_all('option'))} options")
            options = sel.find_all('option')[:5]  # Show first 5
            for opt in options:
                print(f"      {opt.get('value', 'N/A')}: {opt.text.strip()}")
        print()
    
    # Look for lottery results in the page
    print("Looking for lottery numbers in page...")
    
    # Try to find divs or spans with numbers
    all_text = soup.get_text()
    
    # Look for patterns like "3878" or dates
    draw_numbers = re.findall(r'הגרלה.*?(\d{4})', all_text)
    if draw_numbers:
        print(f"Found draw numbers: {draw_numbers[:10]}")
    
    # Look for number patterns
    number_patterns = re.findall(r'\b([1-3]?\d)\s+([1-3]?\d)\s+([1-3]?\d)\s+([1-3]?\d)\s+([1-3]?\d)\s+([1-3]?\d)\b', all_text)
    if number_patterns:
        print(f"Found number patterns: {number_patterns[:3]}")
    
else:
    print(f"Failed to fetch: {response.status_code}")

