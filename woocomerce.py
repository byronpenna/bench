import requests
from bs4 import BeautifulSoup
import json

BASE = "https://arcadenoe.com.gt"
# HEADERS = {"User-Agent": "MiScraperBot/1.0 (+https://miweb.tld/contacto)"}

def extract_products_from_jsonld(obj):
    results = []

    if isinstance(obj, dict):
        if obj.get("@type") == "Product":
            results.append(obj)
        for v in obj.values():
            results.extend(extract_products_from_jsonld(v))

    elif isinstance(obj, list):
        for item in obj:
            results.extend(extract_products_from_jsonld(item))

    return results

def scrape_product(url):
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    products = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            parsed = json.loads(script.string)
            print('parsed', parsed)

            products.extend(extract_products_from_jsonld(parsed))
        except Exception:
            continue

    return products


product_url = BASE + "/products.json"
data = scrape_product(product_url)
print(json.dumps(data, indent=2, ensure_ascii=False))
