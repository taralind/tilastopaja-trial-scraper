import time
import re
import pandas as pd
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import numpy as np


# ------------------------------
# ARGUMENT PARSER
# ------------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="Scrape Tilastopaja athlete trial data.")
    parser.add_argument("--event", type=str, required=True,
                        help="Event code, e.g., 330 for long jump.")
    parser.add_argument("--sex", type=str, required=True,
                        help="Sex code: 1 = men, 2 = women.")
    parser.add_argument("--username", type=str, required=True,
                        help="Tilastopaja username.")
    parser.add_argument("--password", type=str, required=True,
                        help="Tilastopaja password.")
    parser.add_argument("--leaderboard-start-year", type=int, required=True,
                        help="Start year for leaderboard scraping.")
    parser.add_argument("--leaderboard-end-year", type=int, required=True,
                        help="End year for leaderboard scraping.")
    parser.add_argument("--data-start-year", type=int, required=True,
                        help="Start year for athlete trial data scraping.")
    parser.add_argument("--data-end-year", type=int, required=True,
                        help="End year for athlete trial data scraping.")
    return parser.parse_args()

# ------------------------------
# DATA EXTRACTION FUNCTION
# ------------------------------
def extract_full_table_data(rows, year, athlete_name):
    all_rows = []
    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        row_data = [col.text.strip() for col in cols]
        if any(row_data):
            row_data.extend([year, athlete_name])
            all_rows.append(row_data)

    if not all_rows:
        return pd.DataFrame()

    max_cols = max(len(row) for row in all_rows)
    for row in all_rows:
        row.extend([""] * (max_cols - len(row)))

    col_names = [f"col_{i+1}" for i in range(max_cols - 2)] + ["Year", "Athlete"]
    return pd.DataFrame(all_rows, columns=col_names)


# ------------------------------
# GET UNIQUE ATHLETES ACROSS MULTIPLE YEARS
# ------------------------------
def get_all_unique_athletes(driver, base_url, leaderboard_years, sex):
    all_athletes = {}
    pattern = rf'/db/at\.php\?Sex={sex}&ID=\d+'

    for year in leaderboard_years:
        print(f"Fetching athletes from {year} leaderboard...")
        url = base_url.replace("Season=2025", f"Season={year}")
        driver.get(url)
        time.sleep(5)

        links = driver.find_elements(By.TAG_NAME, "a")

        for link in links:
            href = link.get_attribute("href")
            text = link.text.strip()
            if href and re.search(pattern, href):
                match = re.search(r'ID=(\d+)', href)
                if match:
                    athlete_id = match.group(1)
                    full_url = f"https://www.tilastopaja.info/db/at.php?Sex={sex}&ID={athlete_id}"
                    if athlete_id not in all_athletes:
                        all_athletes[athlete_id] = (text, full_url, athlete_id)

    print(f"\nTotal unique athletes across all years: {len(all_athletes)}")
    return list(all_athletes.values())


# ------------------------------
# MAIN SCRAPE FUNCTION
# ------------------------------
def scrape_all_athletes(username_str, password_str, event_code, sex):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Login
    driver.get("https://www.tilastopaja.info/login.php")
    time.sleep(2)
    driver.find_element(By.NAME, "user").send_keys(username_str)
    driver.find_element(By.ID, "password").send_keys(password_str)
    driver.find_element(By.XPATH, "//input[@type='button' and @value='Login']").click()
    time.sleep(3)

    leaderboard_url = (
        f"https://www.tilastopaja.info/db/topeventall.php?"
        f"type=senior&Ind=0&Season=2025&event={event_code}&sex={sex}&top=100&limit=0"
    )

    athletes = get_all_unique_athletes(driver, leaderboard_url, leaderboard_years, sex, leaderboard_years, years)

    all_data = []

    for athlete_name, athlete_url, athlete_id in athletes:
        try:
            driver.get(athlete_url)
            time.sleep(3)

            # DOB
            try:
                dob_element = driver.find_element(By.XPATH, "//b[contains(text(), 'Date of birth:')]")
                dob_text = dob_element.find_element(By.XPATH, "..").text.replace("Date of birth:", "").strip()
            except:
                dob_text = None

            # results per year
            for year in years:
                try:
                    dropdown = Select(driver.find_element(By.NAME, "menupi9"))
                    dropdown.select_by_value(year)
                    time.sleep(4)

                    div = driver.find_element(By.ID, "seasonDiv")
                    table = div.find_element(By.TAG_NAME, "table")
                    rows = table.find_elements(By.TAG_NAME, "tr")

                    tidy_df = extract_full_table_data(rows, year, athlete_name)
                    if not tidy_df.empty:
                        tidy_df["DOB"] = dob_text
                        all_data.append(tidy_df)
                        print(f"{athlete_name} ({year}) — {len(tidy_df)} rows")

                except Exception as e:
                    print(f"Year {year} failed for {athlete_name}: {e}")

        except Exception as e:
            print(f"Skipping athlete {athlete_name}: {e}")

    driver.quit()

    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        print(f"\nScraping done! Total rows: {len(final_df)}")
        return final_df

    print("No data collected.")
    return pd.DataFrame()


# ------------------------------
# RUN SCRIPT
# ------------------------------
if __name__ == "__main__":
    args = parse_args()

    leaderboard_years = [
        str(year) for year in range(
            args.leaderboard_start_year,
            args.leaderboard_end_year + 1
        )
    ]

    years = [
        str(year) for year in range(
            args.data_start_year,
            args.data_end_year + 1
          )
    ]

    final_df = scrape_all_athletes(
        args.username,
        args.password,
        args.event,
        args.sex,
        leaderboard_years,
        years
    )

    if not final_df.empty:
        final_df.replace('', np.nan, inplace=True)

        # processing
        final_df['event_name'] = final_df['col_1'].where(final_df['col_2'].astype(str).str.match(r'^\d{4}$'))
        final_df['event_name'] = final_df['event_name'].ffill().infer_objects()
        final_df = final_df[final_df['col_1'] != final_df['event_name']]
        final_df['col_6'] = final_df['col_6'].ffill()
        final_df['col_7'] = final_df['col_7'].ffill()
        final_df = final_df[final_df['col_1'].isna()]
        columns_to_drop = ['col_1', 'col_5', 'col_8', 'Year', 'Athlete']
        final_df.drop(columns=columns_to_drop, inplace=True)

        def is_numeric(val):
            first_part = str(val).split('/')[0]
            try:
                float(first_part)
                return True
            except ValueError:
                return False

        final_df['col_2'] = final_df['col_2'].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
        final_df['results_list'] = final_df['col_2'].str.split().apply(
            lambda lst: [x for x in lst if is_numeric(x) or x == 'X']
        )
        final_df = final_df.explode('results_list').reset_index(drop=True)
        final_df.rename(columns={'results_list': 'result'}, inplace=True)
        final_df['result'] = final_df['result'].apply(
            lambda x: float(str(x).split('/')[0]) if is_numeric(x) else x
        )
        final_df.drop(columns=['col_2'], inplace=True)

        final_df.rename(columns={
            'col_3': 'year',
            'col_4': 'athlete',
            'col_6': 'location',
            'col_7': 'date',
            'result': 'result'
        }, inplace=True)

        outfile = f"all_athlete_trials_{args.event}_{args.sex}.csv"
        final_df.to_csv(outfile, index=False)
        print(f"\nSaved to {outfile}")
