import requests
import boto3
import pandas as pd
from bs4 import BeautifulSoup
import tempfile
import os

SHOP_URL = "https://arcadenoe.com.gt/products.json"
BUCKET_NAME = "bench-ritsa-bucket"
S3_KEY = "data/products.csv"
HEADERS = {"User-Agent": "MiScraperBot/1.0 (+https://miweb.tld/contacto)"}

# ==============================
# FUNCIONES AUXILIARES
# ==============================
def get_products(url: str):
    """Descarga el JSON de productos desde Shopify"""
    print(f"🔄 Descargando productos desde: {url}")
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data.get("products", [])

def clean_html(html_content: str) -> str:
    """Limpia el HTML (body_html) para dejar solo texto"""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def flatten_product(product: dict):
    """Extrae campos clave y flatea variantes"""
    title = product.get("title")
    description = clean_html(product.get("body_html", ""))
    vendor = product.get("vendor")
    product_type = product.get("product_type")
    tags = ", ".join(product.get("tags", []))
    images = [img["src"] for img in product.get("images", [])]

    rows = []
    for variant in product.get("variants", []):
        rows.append({
            "id": product.get("id"),
            "title": title,
            "description": description,
            "vendor": vendor,
            "type": product_type,
            "tags": tags,
            "variant_title": variant.get("title"),
            "sku": variant.get("sku"),
            "price": variant.get("price"),
            "grams": variant.get("grams"),
            "available": variant.get("available"),
            "image": variant.get("featured_image", {}).get("src") if variant.get("featured_image") else (images[0] if images else None),
            "url": f"{SHOP_URL.replace('/products.json','')}/products/{product.get('handle')}"
        })
    return rows

def upload_to_s3(local_path: str, bucket: str, key: str):
    """Sube archivo local a S3"""
    print(f"Subiendo {local_path} a s3://{bucket}/{key}")
    s3 = boto3.client("s3")
    s3.upload_file(local_path, bucket, key, ExtraArgs={"ContentType": "text/csv"})
    print("Subida completa.")

if __name__ == "__main__":
    products = get_products(SHOP_URL)
    print(f"🛒 {len(products)} productos encontrados")

    all_rows = []
    for p in products:
        all_rows.extend(flatten_product(p))

    df = pd.DataFrame(all_rows)
    print(f"📦 Total variantes procesadas: {len(df)}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        df.to_csv(tmp.name, index=False)
        tmp_path = tmp.name

    # upload_to_s3(tmp_path, BUCKET_NAME, S3_KEY)
    os.remove(tmp_path)
