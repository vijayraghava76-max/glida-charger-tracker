import csv
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://www.google.com/maps/place/GLIDA+Charging+Station/@17.4033087,78.3056974,12659m/data=!3m1!1e3!4m9!1m2!29m1!1b1!3m5!1s0x3bcb96a91fdafdc9:0x13008e89e1162cb7!8m2!3d17.4136024!4d78.3883418!16s%2Fg%2F11x1z5r23y"
CSV_FILE = "glida_charging_data.csv"

ITERATIONS = 30
INTERVAL_SECONDS = 120


def init_csv():
    try:
        with open(CSV_FILE, "x", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["Timestamp", "Connector Type", "Power", "Available", "Total"]
            )
    except FileExistsError:
        pass


def scrape_data(page):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scraped_rows = []

    # Handle Google consent popups if present
    try:
        consent_btn = page.query_selector(
            "button[aria-label*='Accept'], button[aria-label*='Agree']"
        )
        if consent_btn:
            consent_btn.click()
            page.wait_for_timeout(2000)
    except Exception:
        pass

    # Give time for the main side panel to settle
    page.wait_for_timeout(5000)

    # Extract all text from body
    text = page.inner_text("body")

    # Flexible regex patterns for standard Google Maps EV station layouts
    # Matches variations like: "CCS2 60 kW 1/2", "Type 2 · 7 kW 2/2", or "CCS 60kW Available 2 of 4"
    pattern = r"(CCS2?|Type\s*2|GB/T|CHAdeMO)[^\d]*([\d\.]+\s*kW)?.*?(\d+)\s*(?:/|of)\s*(\d+)"
    matches = re.findall(pattern, text, re.IGNORECASE)

    for match in matches:
        conn_type, power, available, total = match
        power_str = power.strip() if power else "N/A"
        scraped_rows.append(
            [timestamp, conn_type.strip(), power_str, available, total]
        )

    # Debug helper: if still empty, log a preview of extracted text
    if not scraped_rows:
        print("\n--- DEBUG: Sample body text extracted ---")
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        print("\n".join(lines[:30]))  # Print first 30 non-empty lines
        print("----------------------------------------\n")

    return scraped_rows


def main():
    init_csv()
    print(
        f"Starting data collection ({ITERATIONS} cycles, every {INTERVAL_SECONDS}s)..."
    )

    with sync_playwright() as p:
        # Launch browser with stealth settings
        browser = p.chromium.launch(
            headless=False,  # Set to False to verify page loading visually
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        for i in range(1, ITERATIONS + 1):
            now_str = datetime.now().strftime("%H:%M:%S")
            print(
                f"[{now_str}] Cycle {i}/{ITERATIONS}: Navigating to Google Maps..."
            )

            try:
                page.goto(URL, wait_until="networkidle", timeout=60000)
                rows = scrape_data(page)

                if rows:
                    with open(
                        CSV_FILE, "a", newline="", encoding="utf-8"
                    ) as f:
                        writer = csv.writer(f)
                        writer.writerows(rows)
                    print(
                        f" -> Successfully logged {len(rows)} connector entries."
                    )
                else:
                    print(
                        " -> No connector status found in this cycle. Retrying..."
                    )

            except Exception as e:
                print(f" -> Error during fetch: {e}")

            if i < ITERATIONS:
                time.sleep(INTERVAL_SECONDS)

        browser.close()

    print("Scraping completed.")


if __name__ == "__main__":
    main()
