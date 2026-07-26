import csv
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://www.google.com/maps/place/GLIDA+Charging+Station/@17.4033087,78.3056974,12659m/data=!3m1!1e3!4m9!1m2!29m1!1b1!3m5!1s0x3bcb96a91fdafdc9:0x13008e89e1162cb7!8m2!3d17.4136024!4d78.3883418!16s%2Fg%2F11x1z5r23y"
CSV_FILE = "glida_charging_data.csv"

def init_csv():
    try:
        with open(CSV_FILE, "x", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Connector Type", "Power", "Available", "Total"])
    except FileExistsError:
        pass

def run_single_tracker():
    init_csv()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Running tracker...")

    with sync_playwright() as p:
        # Crucial flags for GitHub Actions headless environment
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            print("Navigating to URL...")
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            
            # Auto-accept cookies if prompted
            try:
                consent_btn = page.query_selector("button[aria-label*='Accept'], button[aria-label*='Agree']")
                if consent_btn:
                    consent_btn.click()
                    page.wait_for_timeout(2000)
            except Exception:
                pass

            page.wait_for_timeout(5000)

            text = page.inner_text("body")
            pattern = r"(CCS2?|Type\s*2|GB/T|CHAdeMO)[^\d]*([\d\.]+\s*kW)?.*?(\d+)\s*(?:/|of)\s*(\d+)"
            matches = re.findall(pattern, text, re.IGNORECASE)

            scraped_rows = []
            for match in matches:
                conn_type, power, available, total = match
                power_str = power.strip() if power else "N/A"
                scraped_rows.append([timestamp, conn_type.strip(), power_str, available, total])

            if scraped_rows:
                print(f"[SUCCESS] Scraped {len(scraped_rows)} entries.")
                with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerows(scraped_rows)
            else:
                print("[WARNING] No connectors matched pattern.")

        except Exception as e:
            print(f"[ERROR] Run failed: {e}")
            raise e  # Throw error to raise visible exit code if needed
        finally:
            browser.close()

if __name__ == "__main__":
    run_single_tracker()
