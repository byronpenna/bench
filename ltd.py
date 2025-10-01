# requirements: pip install requests beautifulsoup4
import requests
from bs4 import BeautifulSoup
import time
import re
import os

BASE = "https://ejemplo.tld"  # <- cambia por el dominio
HEADERS = {"User-Agent": "MiScraperBot/1.0 (+https://miweb.tld/Contacto)"}
SLEEP = 1.0  # segundos entre requests

def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def find_product_links_from_index(index_url):
    soup = get_soup(index_url)
    links = set()
    # heurística: enlaces que contienen "/product/" o que tengan el tipo product
    for a in soup.select("a[href]"):
        href = a["href"]
        if "/product/" in href or "producto" in href.lower():
            links.add(requests.compat.urljoin(BASE, href))
    return list(links)

def parse_product_page(url):
    soup = get_soup(url)
    # Intenta JSON-LD primero
    ld = soup.find("script", type="application/ld+json")
    if ld:
        try:
            import json
            data = json.loads(ld.string)
            # caso común: data is dict or list
            if isinstance(data, list):
                data = data[0]
            if data.get("@type") == "Product":
                name = data.get("name")
                price = None
                offers = data.get("offers") or {}
                if isinstance(offers, dict):
                    price = offers.get("price")
                images = data.get("image") or []
                if isinstance(images, str):
                    images = [images]
                return {"url": url, "name": name, "price": price, "images": images}
        except Exception:
            pass

    # Fallback: selectores comunes
    title = None
    price = None
    images = []

    # busca microdata
    title_tag = soup.select_one("[itemprop=name]") or soup.select_one("h1")
    if title_tag:
        title = title_tag.get_text(strip=True)

    price_tag = soup.select_one("[itemprop=price]") or soup.select_one(".price") or soup.select_one(".woocommerce-Price-amount")
    if price_tag:
        price = price_tag.get_text(strip=True)

    # imágenes: busca img cuyo src contenga uploads (o dm-content)
    for img in soup.find_all("img", src=True):
        src = img["src"]
        if "dm-content/uploads" in src or "uploads/" in src:
            images.append(requests.compat.urljoin(BASE, src))

    return {"url": url, "name": title, "price": price, "images": list(dict.fromkeys(images))}

def download_images(urls, dest_folder="images"):
    os.makedirs(dest_folder, exist_ok=True)
    for u in urls:
        fn = os.path.basename(u.split("?")[0])
        path = os.path.join(dest_folder, fn)
        try:
            r = requests.get(u, headers=HEADERS, timeout=20)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
            print("guardado", path)
            time.sleep(0.3)
        except Exception as e:
            print("error al bajar", u, e)

if __name__ == "__main__":
    # ejemplo: partir desde la página de categoría o sitemap
    index = BASE + "/tienda/"  # o sitemap.xml
    product_links = find_product_links_from_index(index)
    print("enlaces encontrados:", len(product_links))

    products = []
    for p in product_links:
        try:
            info = parse_product_page(p)
            print(info["name"], info["price"], len(info["images"]))
            products.append(info)
        except Exception as e:
            print("error en", p, e)
        time.sleep(SLEEP)

    # bajar imágenes cuyo path coincida con el patrón dado
    all_images = []
    for pr in products:
        for img in pr.get("images", []):
            if re.search(r"dm-content/uploads/2022/06/", img):
                all_images.append(img)
    download_images(all_images)
