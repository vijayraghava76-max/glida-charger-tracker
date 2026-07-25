import csv
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://www.google.com/maps/place/GLIDA+Charging+Station/@17.4033087,78.3056974,12659m/data=!3m1!1e3!4m9!1m2!29m1!1b1!3m5!1s0x3bcb96a91fdafdc9:0x13008e89e1162cb7!8m2!3d17.4136024!4d78.3883418!16s%2Fg%2F11x1z5r23y"
CSV_FILE = "glida_charging_data.csv"

# Total duration: 1 hour (30 iterations * 120 seconds interval)
ITERATIONS = 30
INTERVAL_SECONDS = 120

def init_csv():
    try:
        with open(CSV_FILE, "x", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Connector Type", "Power", "Available", "Total"])
    except FileExistsError:
        pass

def scrape_data(page):
    # Wait for the page content to stabilize
    page.wait_for_timeout(5000)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scraped_rows = []

    # Get page body text to parse connector blocks
    text = page.inner_text("body")

    # Regular expression to catch patterns like "CCS · 60 kW 6/8" or "Type 2 · 7 kW 2/5"
    pattern = r"(CCS|Type\s*2|GB/T|CHAdeMO)\s*[\cdot·\|-]\s*([\d\.]+\s*kW)[\s\n]*(\d+)/(\d+)"
    matches = re.findall(pattern, text, re.IGNORECASE)

    for match in matches:
        conn_type, power, available, total = match
        scraped_rows.append([timestamp, conn_type.strip(), power.strip(), available, total])

    # Fallback if specific text blocks are structured in separate elements
    if not scraped_rows:
        elements = page.query_selector_all("div, span")
        for el in elements:
            t = el.inner_text().strip()
            m = re.search(r"(CCS|Type\s*2)\s*[\cdot·\|-]\s*([\d\.]+\s*kW)", t, re.IGNORECASE)
            if m:
                scraped_rows.append([timestamp, m.group(1), m.group(2), "N/A", "N/A"])

    return scraped_rows

def main():
    init_csv()
    print(f"Starting 1-hour collection (Fetching every {INTERVAL_SECONDS} seconds)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for i in range(1, ITERATIONS + 1):
            now_str = datetime.now().strftime("%H:%M:%S")
            print(f"[{now_str}] Run {i}/{ITERATIONS}: Fetching Google Maps live status...")
            
            try:
                page.goto(URL, wait_until="networkidle", timeout=60000)
                rows = scrape_data(page)

                if rows:
                    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerows(rows)
                    print(f" Successfully logged {len(rows)} entries.")
                else:
                    print(" Warning: Could not locate charger elements on this cycle.")

            except Exception as e:
                print(f" Error fetching data: {e}")

            if i < ITERATIONS:
                time.sleep(INTERVAL_SECONDS)

        browser.close()

    print(f"Finished 1-hour run. Results saved to {CSV_FILE}.")

if __name__ == "__main__":
    main()
