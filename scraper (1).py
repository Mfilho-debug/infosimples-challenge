from bs4 import BeautifulSoup
import requests
import json
import re
 
URL = 'https://infosimples.com/vagas/desafio/stellarcraft/product.html'
 
response = requests.get(URL)
response.raise_for_status()
soup = BeautifulSoup(response.content, 'html.parser')
 
result = {}
 
def parse_price(text):
    if not text or not text.strip():
        return None
    cleaned = re.sub(r'[^\d,]', '', text.strip()).replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        return None
 
result['title'] = soup.select_one('h1#product_title').get_text(strip=True)
 
result['brand'] = soup.select_one('.product-brand').get_text(strip=True)
 
result['categories'] = [
    a.get_text(strip=True)
    for a in soup.select('.breadcrumb-bar nav a')
]
 
paragraphs = soup.select('#tab-description p')
result['description'] = ' '.join(p.get_text(strip=True) for p in paragraphs)
 
skus = []
for variant in soup.select('.variant-btn'):
    name_el    = variant.select_one('.vname')
    current_el = variant.select_one('.vprice')
    old_el     = variant.select_one('.vprice-old')
    unavailable = 'unavailable' in variant.get('class', [])
 
    if name_el:
        for em in name_el.select('em'):
            em.decompose()
    name = name_el.get_text(strip=True) if name_el else ''
 
    skus.append({
        'name':          name,
        'current_price': parse_price(current_el.get_text() if current_el else None),
        'old_price':     parse_price(old_el.get_text() if old_el else None),
        'available':     not unavailable,
    })
result['skus'] = skus
 
specifications = []
for row in soup.select('.specs-table tr'):
    cells = row.find_all('td')
    if len(cells) >= 2:
        label = cells[0].get_text(strip=True)
        value = cells[1].get_text(strip=True)
        if label and value:
            specifications.append({'label': label, 'value': value})
result['specification'] = specifications
 
reviews = []
for card in soup.select('.review-card'):
    name  = card.select_one('.reviewer-name').get_text(strip=True)
    date  = card.select_one('.reviewer-date').get_text(strip=True)
    text  = card.select_one('.review-text').get_text(strip=True)
    stars = card.select_one('.review-stars').get_text(strip=True)
    reviews.append({
        'name':  name,
        'date':  date,
        'score': stars.count('★'),
        'text':  text,
    })
result['reviews'] = reviews
 
avg_el = soup.select_one('.avg-score')
result['reviews_average_score'] = float(avg_el.get_text(strip=True)) if avg_el else None
 
result['url'] = URL
 
with open('produto.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
 
print('produto.json salvo com sucesso!')
print(json.dumps(result, ensure_ascii=False, indent=2))
