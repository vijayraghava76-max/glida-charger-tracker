import csv
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://www.google.com/maps/place/GLIDA+Charging+Station/@17.4033087,78.3056974,12659m/data=!3m1!1e3!4m9!1m2!29m1!1b1!3m5!1s0x3bcb96a91fdafdc9:0x13008e89e1162cb7!8m2!3d17.4136024!4d78.3883418!16s%2Fg%2F11x1z5r23y"
CSV_FILE = "glida_charging_data.csv"

# 30 iterations * 120 seconds = 60 minutes
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
    # Wait for the main page frame to load completely
    page.wait_for_timeout(6000)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scraped_rows = []

    # Get body inner text to parse connector status blocks
    text = page.inner_text("body")

    # Regular expression matching patterns like "CCS · 60 kW 6/8" or "Type 2 · 7 kW 2/5"
    pattern = r"(CCS|Type\s*2|GB/T|CHAdeMO)\s*[\cdot·\|-]?\s*([\d\.]+\s*kW)?[\s\n]*(\d+)\s*/\s*(\d+)"
    matches = re.findall(pattern, text, re.IGNORECASE)

    for match in matches:
        conn_type, power, available, total = match
        power_str = power.strip() if power else "N/A"
        scraped_rows.append([timestamp, conn_type.strip(), power_str, available, total])

    return scraped_rows

def main():
    init_csv()
    print(f"Starting 1-hour collection (Fetching every {INTERVAL_SECONDS}s)...")

    with sync_playwright() as p:
        # Launch Chromium with custom User-Agent to avoid Google blocking automated headless browsers
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for i in range(1, ITERATIONS + 1):
            now_str = datetime.now().strftime("%H:%M:%S")
            print(f"[{now_str}] Cycle {i}/{ITERATIONS}: Navigating to Google Maps...")

            try:
                page.goto(URL, wait_until="domcontentloaded", timeout=45000)
                rows = scrape_data(page)

                if rows:
                    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerows(rows)
                    print(f" -> Successfully logged {len(rows)} connector entries.")
                else:
                    print(" -> No connector status found in this cycle. Retrying on next loop...")

            except Exception as e:
                print(f" -> Error during fetch: {e}")

            if i < ITERATIONS:
                time.sleep(INTERVAL_SECONDS)

        browser.close()

    print("Scraping completed successfully.")

if __name__ == "__main__":
    main()
