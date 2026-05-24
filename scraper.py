from bs4 import BeautifulSoup
import requests
import json
import re

# ── Configuração ──────────────────────────────────────────────────────────────
URL = 'https://infosimples.com/vagas/desafio/stellarcraft/product.html'

response = requests.get(URL)
response.raise_for_status()
soup = BeautifulSoup(response.content, 'html.parser')

result = {}

# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_price(text):
    """Converte 'R$ 4.799.990,00' -> 4799990.0. Retorna None se inválido."""
    if not text:
        return None
    cleaned = re.sub(r'[^\d,]', '', text.strip()).replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        return None

def text(selector, parent=soup):
    el = parent.select_one(selector)
    return el.get_text(strip=True) if el else ''

# ── title ─────────────────────────────────────────────────────────────────────
result['title'] = text('h1#product_title') or text('h1')

# ── brand ─────────────────────────────────────────────────────────────────────
result['brand'] = text('.product-brand') or text('[class*="brand"]')

# ── categories ────────────────────────────────────────────────────────────────
# O breadcrumb da página tem links "Stellarcraft › Spacecraft › Freighters › ..."
breadcrumb = soup.select('.breadcrumb a, nav[aria-label="breadcrumb"] a, ol.breadcrumb a')
if not breadcrumb:
    # Fallback: qualquer elemento com classe contendo breadcrumb
    bc_el = soup.find(class_=re.compile(r'breadcrumb', re.I))
    breadcrumb = bc_el.find_all('a') if bc_el else []

result['categories'] = [a.get_text(strip=True) for a in breadcrumb if a.get_text(strip=True)]

# ── description ───────────────────────────────────────────────────────────────
# Tab/seção de descrição — tenta várias abordagens
desc_tab = (
    soup.find(id='description') or
    soup.find(id='tab-description') or
    soup.find(class_=re.compile(r'description', re.I))
)
if desc_tab:
    paragraphs = desc_tab.find_all('p')
    result['description'] = ' '.join(p.get_text(strip=True) for p in paragraphs).strip()
else:
    result['description'] = text('.product-description, [class*="description"] p')

# ── skus ──────────────────────────────────────────────────────────────────────
skus = []

# Tenta seletores comuns para lista de variações/configurações
sku_list = (
    soup.select('.sku-item') or
    soup.select('[class*="sku-item"]') or
    soup.select('.configuration-item') or
    soup.select('[class*="config"] li') or
    soup.select('#configurations .item') or
    soup.select('.product-configurations .item')
)

for item in sku_list:
    name_el   = item.select_one('[class*="name"], h3, h4, strong')
    curr_el   = item.select_one('[class*="current-price"], [class*="price-current"], .current-price')
    old_el    = item.select_one('[class*="old-price"], [class*="price-old"], s, del, .old-price')
    unavail   = item.select_one('[class*="unavailable"], [class*="out-of-stock"]')

    name          = name_el.get_text(strip=True) if name_el else ''
    current_price = parse_price(curr_el.get_text() if curr_el else None)
    old_price     = parse_price(old_el.get_text() if old_el else None)
    available     = unavail is None

    if name:
        skus.append({
            'name': name,
            'current_price': current_price,
            'old_price': old_price,
            'available': available,
        })

result['skus'] = skus

# ── specification ─────────────────────────────────────────────────────────────
specifications = []

spec_section = (
    soup.find(id='specifications') or
    soup.find(id='specs') or
    soup.find(class_=re.compile(r'spec', re.I))
)

rows = spec_section.select('tr') if spec_section else soup.select('#specifications tr, .specifications tr')

for row in rows:
    cells = row.find_all(['th', 'td'])
    if len(cells) >= 2:
        label = cells[0].get_text(strip=True)
        value = cells[1].get_text(strip=True)
        if label and value:
            specifications.append({'label': label, 'value': value})

result['specification'] = specifications

# ── reviews ───────────────────────────────────────────────────────────────────
reviews = []

review_els = (
    soup.select('.review-item') or
    soup.select('[class*="review-card"]') or
    soup.select('[class*="review-block"]') or
    soup.select('#reviews .review') or
    soup.select('.reviews .review')
)

for rev in review_els:
    name_el  = rev.select_one('[class*="name"], [class*="author"], strong')
    date_el  = rev.select_one('[class*="date"], time')
    stars_el = rev.select_one('[class*="star"], [class*="score"], [class*="rating"]')
    text_el  = rev.select_one('[class*="text"], [class*="body"], [class*="comment"], p')

    name = name_el.get_text(strip=True) if name_el else ''
    date = date_el.get_text(strip=True) if date_el else ''
    body = text_el.get_text(strip=True) if text_el else ''

    # Conta estrelas ★ para obter o score
    score = 0
    if stars_el:
        stars_text = stars_el.get_text()
        score = stars_text.count('★')
        if score == 0:
            m = re.search(r'\d+', stars_text)
            score = int(m.group()) if m else 0

    if name:
        reviews.append({
            'name': name,
            'date': date,
            'score': score,
            'text': body,
        })

result['reviews'] = reviews

# ── reviews_average_score ─────────────────────────────────────────────────────
avg_el = (
    soup.select_one('[class*="average-score"]') or
    soup.select_one('[class*="rating-average"]') or
    soup.select_one('[class*="rating-value"]') or
    soup.select_one('[class*="review-score"]')
)

if avg_el:
    m = re.search(r'[\d]+[,\.][\d]+|[\d]+', avg_el.get_text(strip=True))
    result['reviews_average_score'] = float(m.group().replace(',', '.')) if m else None
elif reviews:
    scores = [r['score'] for r in reviews if r['score'] > 0]
    result['reviews_average_score'] = round(sum(scores) / len(scores), 1) if scores else None
else:
    result['reviews_average_score'] = None

# ── url ───────────────────────────────────────────────────────────────────────
result['url'] = URL

# ── Salva produto.json ────────────────────────────────────────────────────────
with open('produto.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print('produto.json salvo com sucesso!')
print(json.dumps(result, ensure_ascii=False, indent=2))
