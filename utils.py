"""This file contains utility functions for the live and upcoming events data scraper."""


import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import json
import os
import random
from urllib.parse import urljoin
import csv
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# # SoccerData imports (install with: pip install soccerdata)
# try:
#     import soccerdata as sd
#     SOCCERDATA_AVAILABLE = True
#     # print("✅ SoccerData library available")
# except ImportError:
#     SOCCERDATA_AVAILABLE = False
#     # print("⚠️ SoccerData library not installed. Run: pip install soccerdata")


def get_random_headers():
    """Load and return a random set of headers from the JSON file."""
    # Get the directory where the current script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    headers_file = os.path.join(script_dir, 'browser_headers.json')

    try:
        with open(headers_file, 'r') as f:
            headers_list = json.load(f)

        # Return a random set of headers
        return random.choice(headers_list)

    except FileNotFoundError:
        # Fallback to your original headers if file not found
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }


def scrape_sb_live():
    """
    Scrapes SportyBet live football matches and extracts halftime data
    Returns a list of dictionaries containing match data
    """
    url = "https://www.sportybet.com/ng/sport/football/live_list"

    # Headers to mimic a real browser
    headers = get_random_headers()

    # # Test for blocks with a quick HTTP request
    # try:
    #     response = requests.get(url, headers=headers, timeout=10)
    #     print(f"Response status: {response.status_code}")
    #     if response.status_code in [403, 429]:
    #         print("❌ Blocked: Rate limit or IP ban detected")
    #         return []
    #     if not response.text.strip() or "blocked" in response.text.lower():
    #         print("❌ Blocked: Empty response or block page detected")
    #         return []
    # except requests.exceptions.RequestException as e:
    #     print(f"❌ HTTP check failed: {e}")
    #     return []

    # print("🌐 Fetching data...")

    try:
        # Set up headless Chrome
        chrome_options = Options()
        # Run without opening a browser window
        chrome_options.add_argument("--headless")
        # For stability in some environments
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument(
            "--disable-dev-shm-usage")  # Avoid resource issues
        chrome_options.add_argument("--disable-gpu")  # Additional stability
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-logging")  # Reduce log noise
        chrome_options.add_argument("--log-level=3")  # Only fatal errors
        # Reuse your user-agent for consistency
        chrome_options.add_argument(f"user-agent={headers['User-Agent']}")

        # Initialize driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # print("🛠️ Initializing browser...")
        driver.get(url)

        # Random delay to mimic human behavior
        time.sleep(random.uniform(1, 3))

        # Wait for JS to load (adjust timeout if needed; 10 seconds should suffice for this site)
        driver.implicitly_wait(10)

        # print("✅ Page loaded with JS rendered")

        # Get page source and clean it before parsing
        page_source = driver.page_source

        # Clean the page source to remove any problematic content
        # Remove any WebDriver-related paths that might be causing issues
        page_source = re.sub(
            r'/[^<>]*?\.wdm/[^<>]*?chromedriver[^<>]*?', '', page_source)
        page_source = re.sub(
            r'\[[^<>\[\]]*?chromedriver[^<>\[\]]*?\]', '', page_source)

        # Parse with explicit parser and error handling
        try:
            # Try html.parser first (most robust)
            soup = BeautifulSoup(page_source, 'html.parser')
        except Exception as e1:
            print(f"⚠️ html.parser failed: {e1}")
            try:
                # Fallback to lxml if available
                soup = BeautifulSoup(page_source, 'lxml')
            except Exception as e2:
                print(f"⚠️ lxml parser failed: {e2}")
                # Last resort - use html5lib if available
                try:
                    soup = BeautifulSoup(page_source, 'html5lib')
                except Exception as e3:
                    print(f"❌ All parsers failed. html5lib error: {e3}")
                    return []

        # # Parse the fully rendered HTML
        # soup = BeautifulSoup(driver.page_source, 'html.parser')

        # driver.quit()  # Clean up browser session

        # Find all matches with the correct class structure
        matches = soup.find_all(
            'div', class_='m-table-row m-content-row match-row football-row')
        # print(f"Found {len(matches)} ongoing events")

        extracted_data = []
        halftime_matches = 0
        first_half_matches = 0
        second_half_matches = 0
        zero_goal_matches = 0
        one_goal_matches = 0

        # # Load watchlist CSV
        # try:
        #     watchlist_df = pd.read_csv('watchlist_today.csv')
        #     watchlist_titles = set(watchlist_df['title'])  # Convert titles to a set for O(1) lookup
        # except Exception as e:
        #     print(f"⚠️ Could not load watchlist_today.csv: {e}")
        #     watchlist_titles = set()

        for match in matches:
            try:
                # Check if this is a halftime match
                left_team_cell = match.find(
                    class_='m-table-cell left-team-cell')
                is_halftime = False
                is_first_half = False
                is_second_half = False

                if left_team_cell:
                    left_team_table = left_team_cell.find(
                        class_='left-team-table')
                    if left_team_table:
                        game_id_elem = left_team_table.find(class_='game-id')
                        if game_id_elem:
                            time_text = game_id_elem.get_text(
                                strip=True).upper()
                            # print(f"Game ID text: {time_text}")  # Debug output
                            is_halftime = any(x in time_text for x in [
                                              'HT', 'HALF', 'HALFTIME', 'HALF-TIME'])
                            is_first_half = any(x in time_text for x in [
                                                'H1', '1ST', 'FIRST'])
                            is_second_half = any(x in time_text for x in [
                                                 'H2', '2ND', 'SECOND'])

                # Skip if not a halftime, first half, or second half match
                if not (is_halftime or is_first_half or is_second_half):
                    continue

                # Update counters
                if is_halftime:
                    halftime_matches += 1
                if is_first_half:
                    first_half_matches = first_half_matches + \
                        1 if 'first_half_matches' in locals() else 1
                if is_second_half:
                    second_half_matches = second_half_matches + \
                        1 if 'second_half_matches' in locals() else 1

                # Find teams container
                teams_container = match.find(class_='teams')
                if not teams_container:
                    continue

                # Extract team names
                home_team_elem = teams_container.find(class_='home-team')
                away_team_elem = teams_container.find(class_='away-team')

                if not home_team_elem or not away_team_elem:
                    continue

                home_team = home_team_elem.get_text(strip=True)
                away_team = away_team_elem.get_text(strip=True)

                # Extract title from teams container
                title = teams_container.get(
                    'title', f"{home_team} vs {away_team}")

                # Find score container
                score_container = match.find(class_='score')
                if not score_container:
                    continue

                # Find score items
                score_items = score_container.find_all(class_='score-item')
                if len(score_items) < 2:
                    continue

                # Extract scores and convert to integers
                try:
                    home_score = int(score_items[0].get_text(strip=True))
                    away_score = int(score_items[1].get_text(strip=True))
                    total_goals = home_score + away_score
                except (ValueError, IndexError):
                    continue

                # Matches with 0 total goals at HT
                if total_goals == 0 and is_halftime:
                    match_data = {
                        'title': title,
                        'home-team': home_team,
                        'away-team': away_team,
                        'home_ht_goals': home_score,
                        'away_ht_goals': away_score,
                        'ht_goals': total_goals
                    }
                    extracted_data.append(match_data)
                    zero_goal_matches += 1
                    print(f"| 👀 0aHT: {home_team} vs {away_team} |")
                    # # Check if in watchlist
                    # if title in watchlist_titles:
                    #     print(f"👀⭐ Watchlist event: {home_team} vs {away_team}")
                    # else:
                    #     print(f"👀 0-goal HT event: {home_team} vs {away_team}")

                # Matches with 1 total goals at HT
                if total_goals == 1 and is_halftime:
                    new_match_data = {
                        'title': title,
                        'home-team': home_team,
                        'away-team': away_team,
                        'home_ht_goals': home_score,
                        'away_ht_goals': away_score,
                        'ht_goals': total_goals
                    }
                    extracted_data.append(new_match_data)
                    one_goal_matches += 1
                    print(f"| 💡 1aHT: {home_team} vs {away_team} |")

            except Exception as e:
                print(f"⚠️ Error processing match: {e}")
                continue

        # print(f"\n📊 Summary:")
        # print(f"   - Total events found: {len(matches)}")
        print(
            f"   - HT: {halftime_matches}, H1: {first_half_matches}, H2: {second_half_matches}")
        print(f"   - 0aHT: {zero_goal_matches}")
        print(f"   - 1aHT: {one_goal_matches}")

        return extracted_data

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching data: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return []


def scrape_sb_today():
    """
    Scrapes SportyBet today's football matches and extracts match data
    Returns a list of dictionaries containing match data
    """
    url = "https://www.sportybet.com/ng/sport/football/today"
    current_date = datetime.now().strftime('%d-%m-%y')

    # Headers to mimic a real browser
    headers = get_random_headers()

    # # Test for blocks with a quick HTTP request
    # try:
    #     response = requests.get(url, headers=headers, timeout=10)
    #     # print(f"Response status: {response.status_code}")
    #     if response.status_code in [403, 429]:
    #         print("❌ Blocked: Rate limit or IP ban detected")
    #         return []
    #     if not response.text.strip() or "blocked" in response.text.lower():
    #         print("❌ Blocked: Empty response or block page detected")
    #         return []
    # except requests.exceptions.RequestException as e:
    #     print(f"❌ HTTP check failed: {e}")
    #     return []

    try:
        # Set up headless Chrome
        chrome_options = Options()
        # Run without opening a browser window
        chrome_options.add_argument("--headless")
        # For stability in some environments
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument(
            "--disable-dev-shm-usage")  # Avoid resource issues
        chrome_options.add_argument("--disable-gpu")  # Additional stability
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-logging")  # Reduce log noise
        chrome_options.add_argument("--log-level=3")  # Only fatal errors
        # Reuse your user-agent for consistency
        chrome_options.add_argument(f"user-agent={headers['User-Agent']}")

        # Initialize driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get(url)

        # time.sleep(random.uniform(1, 3))  # Random delay to mimic human behavior

        # Wait for JS to load (adjust timeout if needed; 10 seconds should suffice for this site)
        driver.implicitly_wait(10)

        page_count = 0
        all_extracted_data = []

        while True:
            page_count += 1
            # print(f"📄 Processing page {page_count}...")
            time.sleep(random.uniform(1, 3))

            # Get page source and clean it before parsing
            page_source = driver.page_source

            # Clean the page source to remove any problematic content
            # Remove any WebDriver-related paths that might be causing issues
            page_source = re.sub(
                r'/[^<>]*?\.wdm/[^<>]*?chromedriver[^<>]*?', '', page_source)
            page_source = re.sub(
                r'\[[^<>\[\]]*?chromedriver[^<>\[\]]*?\]', '', page_source)

            # Parse with explicit parser and error handling
            try:
                # Try html.parser first (most robust)
                soup = BeautifulSoup(page_source, 'html.parser')
            except Exception as e1:
                print(f"⚠️ Parser failed on page {page_count + 1}: {e1}")
                break
            # except Exception as e1:
            #     print(f"⚠️ html.parser failed: {e1}")
            #     try:
            #         # Fallback to lxml if available
            #         soup = BeautifulSoup(page_source, 'lxml')
            #     except Exception as e2:
            #         print(f"⚠️ lxml parser failed: {e2}")
            #         # Last resort - use html5lib if available
            #         try:
            #             soup = BeautifulSoup(page_source, 'html5lib')
            #         except Exception as e3:
            #             print(f"❌ All parsers failed. html5lib error: {e3}")
            #             driver.quit()
            #             return []

            # Find all matches with the correct class structure
            matches = soup.find_all(
                'div', class_='m-table-row m-content-row match-row')

            for match in matches:
                try:
                    # Extract tournament name from parent match-league
                    tournament = "Unknown Tournament"
                    time_text = ""
                    game_id_text = ""
                    game_id_match = None

                    match_league = match.find_parent(
                        'div', class_='match-league')
                    if match_league:
                        league_title = match_league.find(
                            'div', class_='league-title')
                        if league_title:
                            text_span = league_title.find(
                                'span', class_='text')
                            if text_span:
                                tournament = text_span.get_text(strip=True)

                    left_team_cell = match.find(
                        class_='m-table-cell left-team-cell')

                    if left_team_cell:
                        left_team_table = left_team_cell.find(
                            class_='left-team-table')
                        if left_team_table:
                            game_id_elem = left_team_table.find(
                                class_='game-id')
                            if game_id_elem:
                                game_id_text = game_id_elem.get_text(
                                    strip=True)
                                # Extract 5-digit number using regex
                                game_id_match = re.search(
                                    r'\b\d{5}\b', game_id_text)
                                # if game_id_match:
                                #     match_data['game_id'] = game_id_match.group()
                                # else:
                                #     match_data['game_id'] = game_id_text  # Fallback to full text if no 5-digit found

                            # Extract time
                            time_elem = left_team_table.find(
                                class_='clock-time')
                            if time_elem:
                                time_text = time_elem.get_text(strip=True)

                    # Find teams container
                    teams_container = match.find(class_='teams')
                    if not teams_container:
                        continue

                    # Extract team names
                    home_team_elem = teams_container.find(class_='home-team')
                    away_team_elem = teams_container.find(class_='away-team')

                    if not home_team_elem or not away_team_elem:
                        continue

                    home_team = home_team_elem.get_text(strip=True)
                    away_team = away_team_elem.get_text(strip=True)

                    # Extract title from teams container
                    title = teams_container.get(
                        'title', f"{home_team} vs {away_team}")

                    # Extract odds
                    pre_match_odds_home = ""
                    pre_match_odds_draw = ""
                    pre_match_odds_away = ""

                    market_cell = match.find(
                        'div', class_='m-table-cell market-cell two-markets')
                    if market_cell:
                        m_market = market_cell.find(
                            'div', class_='m-market market')
                        if m_market:
                            outcomes = m_market.find_all(
                                'div', class_='m-outcome')
                            if len(outcomes) >= 3:
                                # Extract odds from each outcome
                                home_odds = outcomes[0].find(
                                    'span', class_='m-outcome-odds')
                                draw_odds = outcomes[1].find(
                                    'span', class_='m-outcome-odds')
                                away_odds = outcomes[2].find(
                                    'span', class_='m-outcome-odds')

                                pre_match_odds_home = home_odds.get_text(
                                    strip=True) if home_odds else ""
                                pre_match_odds_draw = draw_odds.get_text(
                                    strip=True) if draw_odds else ""
                                pre_match_odds_away = away_odds.get_text(
                                    strip=True) if away_odds else ""

                    match_data = {
                        'date': current_date,
                        'time': time_text,
                        'title': title,
                        'tournament': tournament,
                        'game-id': game_id_match.group() if game_id_match else game_id_text,
                        'home-team': home_team,
                        'away-team': away_team,
                        'pre-match_odds_home': pre_match_odds_home,
                        'pre-match_odds_draw': pre_match_odds_draw,
                        'pre-match_odds_away': pre_match_odds_away,
                    }
                    all_extracted_data.append(match_data)

                except Exception as e:
                    print(f"⚠️ Error processing match: {e}")
                    continue

            # print(f"Found {len(matches)} matches on page {page_count}")

            # Check if there are more pages
            if not check_and_navigate_pagination(driver):
                break

            if page_count > 50:  # Safety limit
                print("⚠️ Reached page limit")
                break

        driver.quit()  # Clean up browser session

        # Convert extracted_data to DataFrame for top 5 kick-off times
        df = pd.DataFrame(all_extracted_data)
        total_matches = len(all_extracted_data)
        print(f"There are {total_matches} more upcoming events today")
        if not df.empty and 'time' in df.columns:
            top_times = df['time'].value_counts().head(5)
            print(f"\n⏱️ Top 5 kick-off time:")
            for kick_time, count in top_times.items():
                print(f"  - {count} events at {kick_time}.")
        else:
            print(f"\n⏱️ Top 5 kick-off time: No data available")

        return all_extracted_data

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching data: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return []


def save_to_csv(data, filename=None):
    """
    Save extracted data to CSV file with timestamp
    """
    if not data:
        print("❌ No data to save")
        return False, None

    if filename is None:
        # Generate filename with current timestamp
        current_time = datetime.now()
        filename = f"sb_default_{current_time.strftime('%d-%m-%y-%H-%M-%S')}.csv"

    try:
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        print(f"💾 Data saved to {filename}")
        return True, filename
    except Exception as e:
        print(f"❌ Error saving to CSV: {e}")
        return False, None


def append_to_csv(data, filename):
    """
    Append new data to an existing CSV file, avoiding duplicates based on 'title'

    Args:
        data (list): List of dictionaries containing new scraped data
        filename (str): Path to the existing CSV file

    Returns:
        tuple: (bool, int) - Success status and number of new records appended
    """

    if not data:
        print("❌ No data to append")
        return False, 0

    try:
        # Create DataFrame from new data
        new_df = pd.DataFrame(data)

        if not os.path.exists(filename):
            # File doesn't exist, create it
            new_df.to_csv(filename, index=False, quoting=0, escapechar='\\')
            print(f"💾 Created {filename} with {len(new_df)} records")
            return True, len(new_df)

        # Load existing data
        # existing_df = pd.read_csv(filename, quoting=0, escapechar='\\')
        existing_df = pd.read_csv(filename)

        # Get existing titles to check for duplicates
        existing_titles = set(existing_df['title'].tolist())

        # Filter out duplicates
        unique_records = new_df[~new_df['title'].isin(existing_titles)]

        if unique_records.empty:
            print(f"⏭️ All {len(new_df)} records were duplicates - no new data appended")
            return True, 0

        # Append unique records to existing data
        updated_df = pd.concat([existing_df, unique_records], ignore_index=True)

        # Save updated data back to CSV
        updated_df.to_csv(filename, index=False)

        print(f"📝 Appended {len(unique_records)} new records to {filename}")
        return True, len(unique_records)

    except Exception as e:
        print(f"❌ Error appending to {filename}: {e}")
        return False, 0


def update_alert_log(extracted_data):
    """
    Updates alerts_log.csv with new match data while avoiding duplicates
    Also merges tournament and odds data from today.csv based on date and title

    Args:
        extracted_data (list): List of dictionaries containing match data from scrape_sb_live()

    Returns:
        int: Number of new records added
    """

    # Define the CSV file paths
    csv_file = os.getenv('ALERT_LOG_FILE', 'alerts_log.csv')
    today_csv = 'today.csv'

    # Get current date and time
    current_date = datetime.now().strftime('%d-%m-%y')
    current_time = datetime.now().strftime('%H:%M')

    # Check if extracted_data is empty
    if not extracted_data:
        return 0

    # Load today.csv for tournament and odds data
    today_df = None
    if os.path.exists(today_csv):
        try:
            today_df = pd.read_csv(today_csv, quoting=0, escapechar='\\')
        except Exception as e:
            print(f"⚠️ Error loading today.csv: {e}")

    # Prepare new data with additional columns
    new_records = []
    for match in extracted_data:
        new_record = {
            'date': current_date,
            'log_time': current_time,
            'tournament': '',
            'title': match['title'],
            'home-team': match['home-team'],
            'away-team': match['away-team'],
            'pre-match_odds_home': '' if match.get('pre-match_odds_home', '') == '' else float(match.get('pre-match_odds_home', '')) if str(match.get('pre-match_odds_home', '')).replace('.', '').isdigit() else '',
            'pre-match_odds_draw': '' if match.get('pre-match_odds_draw', '') == '' else float(match.get('pre-match_odds_draw', '')) if str(match.get('pre-match_odds_draw', '')).replace('.', '').isdigit() else '',
            'pre-match_odds_away': '' if match.get('pre-match_odds_away', '') == '' else float(match.get('pre-match_odds_away', '')) if str(match.get('pre-match_odds_away', '')).replace('.', '').isdigit() else '',
            'home_ht_goals': match['home_ht_goals'],
            'away_ht_goals': match['away_ht_goals'],
            'ht_goals': int(match['ht_goals'])  # Assuming you want ht_goals as integer, per previous discussion
        }
        # new_record = {
        #     'date': current_date,
        #     'log_time': current_time,
        #     'tournament': '',
        #     'title': match['title'],
        #     'home-team': match['home-team'],
        #     'away-team': match['away-team'],
        #     'pre-match_odds_home': '',
        #     'pre-match_odds_draw': '',
        #     'pre-match_odds_away': '',
        #     'home_ht_goals': match['home_ht_goals'],
        #     'away_ht_goals': match['away_ht_goals'],
        #     'ht_goals': int(match['ht_goals'])
        # }

        # Try to find matching record in today.csv
        if today_df is not None:
            today_df['date'] = today_df['date'].astype(str).str.strip()
            matching_row = today_df[
                (today_df['date'] == current_date) &
                (today_df['title'].str.strip() == match['title'].strip())
            ]

            if not matching_row.empty:
                row = matching_row.iloc[0]
                new_record['tournament'] = row.get('tournament', '')
                new_record['pre-match_odds_home'] = row.get(
                    'pre-match_odds_home', '')
                new_record['pre-match_odds_draw'] = row.get(
                    'pre-match_odds_draw', '')
                new_record['pre-match_odds_away'] = row.get(
                    'pre-match_odds_away', '')
            else:
                print(f"🔍 No match found for date: '{current_date}' and title: '{match['title']}'")

        new_records.append(new_record)

    # Create DataFrame from new records
    new_df = pd.DataFrame(new_records)

    try:
        # Check if the CSV file exists
        if os.path.exists(csv_file):
            # Load existing data
            existing_df = pd.read_csv(csv_file, quoting=0, escapechar='\\', dtype={
                'tournament': 'object',
                'pre-match_odds_home': 'float64',
                'pre-match_odds_draw': 'float64',
                'pre-match_odds_away': 'float64',
                'home_ht_goals': 'Int64',
                'away_ht_goals': 'Int64',
                'ht_goals': 'Int64'
            })

            # Get existing titles to check for duplicates
            existing_titles = set(existing_df['title'].tolist())

            # Filter out duplicates from new data
            unique_records = []
            duplicate_count = 0

            for record in new_records:
                if record['title'] not in existing_titles:
                    unique_records.append(record)
                else:
                    duplicate_count += 1

            if unique_records:
                # Create DataFrame from unique records
                unique_df = pd.DataFrame(unique_records)

                # Append unique records to existing data
                updated_df = pd.concat(
                    [existing_df, unique_df], ignore_index=True)

                # Save updated data back to CSV
                updated_df.to_csv(csv_file, index=False,
                                  quoting=0, escapechar='\\')

                print(
                    f"📝 Added {len(unique_records)} new records to alerts_log.csv")
                if duplicate_count > 0:
                    print(f"⏭️ Skipped {duplicate_count} duplicate records")

                return len(unique_records)
            else:
                print(
                    f"⏭️ All {len(new_records)} records were duplicates - no new data saved")
                return 0

        else:
            # File doesn't exist, create new one with headers
            new_df.to_csv(csv_file, index=False, quoting=0, escapechar='\\')
            return len(new_records)

    except Exception as e:
        print(f"❌ Error updating alerts_log.csv: {e}")
        return 0


def display_results(filename=None):
    """
    Read and display the CSV file contents
    """
    try:
        if filename is None:
            print("❌ No filename provided")
            return None

        df = pd.read_csv(filename)
        print(f"\n📋 Contents of {filename}:")
        print("=" * 60)
        print(df.to_string(index=False))
        print(f"\n📈 Dataset Info:")
        print(f"   - Shape: {df.shape}")
        print(f"   - Columns: {list(df.columns)}")
        return df
    except FileNotFoundError:
        print(f"❌ File {filename} not found")
        return None
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return None


def calculate_total_goals(score_text):
    """
    Extract and calculate total goals from score string like '0:2 ' or '1:4 '
    """
    try:
        # Clean the score text and extract numbers
        score_clean = score_text.strip().replace(' ', '')
        if ':' in score_clean:
            home_goals, away_goals = score_clean.split(':')
            return int(home_goals) + int(away_goals)
        return 0
    except (ValueError, AttributeError):
        return 0


def select_date(driver, target_date):
    """
    Select a specific date from the dropdown
    Args:
        driver: Selenium WebDriver instance
        target_date: Date string in format "05/09/2025"
    """
    try:
        # print(f"🗓️ Attempting to select date: {target_date}")

        # Wait for the date dropdown to be present
        wait = WebDriverWait(driver, 20)

        # Try to find and click the dropdown
        dropdown_selectors = [
            ".m-select-list",
            ".optionEvent .m-select-list",
            "[class*='select-list']"
        ]

        dropdown_element = None
        for selector in dropdown_selectors:
            try:
                dropdown_element = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                # print(f"✅ Found dropdown with selector: {selector}")
                break
            except TimeoutException:
                continue

        if not dropdown_element:
            print("❌ Could not find date dropdown")
            return False

        # Click the dropdown to open it
        driver.execute_script("arguments[0].click();", dropdown_element)
        time.sleep(2)

        # Look for date options
        date_options = driver.find_elements(
            By.CSS_SELECTOR, ".m-select-list span, .select-index")

        # If no options found, try alternative selectors
        if not date_options:
            date_options = driver.find_elements(
                By.XPATH, f"//*[contains(text(), '{target_date}')]")

        for option in date_options:
            try:
                option_text = option.text.strip()
                # print(f"🔍 Found date option: '{option_text}'")

                if target_date in option_text:
                    # print(f"✅ Selecting date: {target_date}")
                    driver.execute_script("arguments[0].click();", option)
                    time.sleep(3)  # Wait for page to reload with new date
                    return True
            except Exception as e:
                print(f"⚠️ Error checking date option: {e}")
                continue

        print(f"❌ Date '{target_date}' not found in available options")
        return False

    except Exception as e:
        print(f"❌ Error selecting date: {e}")
        return False


def check_and_navigate_pagination(driver):
    """
    Check if there are more pages and navigate to the next one
    Returns True if successfully navigated to next page, False if no more pages
    """
    try:
        # Look for next page button - try multiple selectors
        next_selectors = [
            ".pagination .pageNum.icon-next:not(.icon-disabled)",
            ".pagination .icon-next:not(.icon-disabled)",
            "[class*='icon-next']:not([class*='disabled'])"
        ]

        for selector in next_selectors:
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, selector)
                if next_button and "icon-disabled" not in next_button.get_attribute("class"):
                    # print("📄 Navigating to next page...")
                    driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(3)  # Wait for page to load
                    return True
            except NoSuchElementException:
                continue

        # print("📄 No more pages available")
        return False

    except Exception as e:
        print(f"⚠️ Error checking pagination: {e}")
        return False


def extract_match_data(soup):
    """
    Extract match data from the parsed HTML
    Returns list of dictionaries with match information
    """
    matches = []

    try:
        # Find the result list section
        result_section = soup.find("section", class_="result-list")
        if not result_section:
            print("❌ Could not find result-list section")
            return matches

        # Find all tournament blocks (dl elements)
        tournament_blocks = result_section.find_all("dl", class_="list")
        # print(f"🏆 Found {len(tournament_blocks)} tournament blocks")

        for block in tournament_blocks:
            try:
                # Get tournament name from dt tag
                dt_tag = block.find("dt")
                tournament = dt_tag.get_text(
                    strip=True) if dt_tag else "Unknown Tournament"
                # Remove any surrounding double quotes
                tournament = tournament.strip('"')
                # print(f"🏆 Processing tournament: {tournament}")

                # Find all matches in this tournament (dd tags)
                matches_in_tournament = block.find_all("dd")
                # print(
                #     f"⚽ Found {len(matches_in_tournament)} matches in {tournament}")

                for match_dd in matches_in_tournament:
                    try:
                        # Find the result-event ul
                        result_event = match_dd.find(
                            "ul", class_="result-event")
                        if not result_event:
                            continue

                        # Extract home team, away team, and score
                        home_li = result_event.find("li", class_="home")
                        away_li = result_event.find("li", class_="away")
                        score_li = result_event.find("li", class_="score")

                        if home_li and away_li and score_li:
                            home_team = home_li.get_text(strip=True)
                            away_team = away_li.get_text(strip=True)

                            # Extract score from score-com div - handle two different structures
                            score_div = score_li.find(
                                "div", class_="score-com")
                            if score_div:
                                score_detail = score_div.find(
                                    "div", class_="score-detail")

                                if score_detail:
                                    # Structure with halftime data - score is in score-com but outside score-detail
                                    # Get direct text content from score-com, excluding nested elements
                                    score_com_children = list(
                                        score_div.children)
                                    score_text = ""
                                    for child in score_com_children:
                                        if hasattr(child, 'name') and child.name:
                                            # Skip nested div elements
                                            continue
                                        else:
                                            # Get text nodes directly in score-com
                                            score_text += str(child).strip()

                                    # If no direct text found, try alternative extraction
                                    if not score_text or not any(c.isdigit() for c in score_text):
                                        full_text = score_div.get_text(
                                            separator='|', strip=True)
                                        detail_text = score_detail.get_text(
                                            strip=True)
                                        parts = full_text.split('|')
                                        # Look for the part that's not the halftime score
                                        for part in parts:
                                            if part.strip() != detail_text and ':' in part:
                                                score_text = part.strip()
                                                break
                                else:
                                    # Simple structure - score is directly in score-com
                                    score_text = score_div.get_text(strip=True)

                                # Extract scores and convert to integers

                                try:
                                    # Clean the score text and extract numbers
                                    score_clean = score_text.strip().replace(' ', '')
                                    if ':' in score_clean:
                                        home_ft_goals, away_ft_goals = score_clean.split(
                                            ':')
                                        ft_goals = int(
                                            home_ft_goals) + int(away_ft_goals)
                                except (ValueError, AttributeError):
                                    continue

                                ft_goals = calculate_total_goals(score_text)

                                match_data = {
                                    'tournament': tournament,
                                    'home_team': home_team,
                                    'away_team': away_team,
                                    'home_ft_goals': int(home_ft_goals),
                                    'away_ft_goals': int(away_ft_goals),
                                    'ft_goals': ft_goals
                                }
                                matches.append(match_data)
                                # print(
                                #     f"✅ Extracted: {home_team} vs {away_team} ({ft_goals} goals)")

                    except Exception as e:
                        print(f"⚠️ Error processing individual match: {e}")
                        continue

            except Exception as e:
                print(f"⚠️ Error processing tournament block: {e}")
                continue

    except Exception as e:
        print(f"❌ Error in extract_match_data: {e}")

    return matches


def scrape_sb_results(target_date):
    """
    Main scraping function for sb live results
    Args:
        target_date: Date string in format "05/09/2025"
    """
    url = "https://www.sportybet.com/ng/liveResult/"
    headers = get_random_headers()
    all_matches = []

    try:
        # print(f"🚀 Starting scraper for date: {target_date}")

        # Set up headless Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument(f"user-agent={headers['User-Agent']}")
        chrome_options.add_argument("--window-size=1920,1080")

        # Initialize driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # print("🌐 Loading sb page...")
        driver.get(url)

        # Wait for initial page load
        time.sleep(random.uniform(3, 5))

        # Select the target date
        if not select_date(driver, target_date):
            print("❌ Failed to select target date")
            driver.quit()
            return []

        page_count = 1

        # Process all pages for the selected date
        while True:
            # print(f"📄 Processing page {page_count}...")

            # Wait for content to load
            time.sleep(random.uniform(2, 4))

            # Get page source and parse
            page_source = driver.page_source

            # Clean the page source
            page_source = re.sub(
                r'/[^<>]*?\.wdm/[^<>]*?chromedriver[^<>]*?', '', page_source)
            page_source = re.sub(
                r'\[[^<>\[\]]*?chromedriver[^<>\[\]]*?\]', '', page_source)

            # Parse with BeautifulSoup
            try:
                soup = BeautifulSoup(page_source, 'html.parser')
            except Exception as e1:
                print(f"⚠️ html.parser failed: {e1}")
                try:
                    soup = BeautifulSoup(page_source, 'lxml')
                except Exception as e2:
                    print(f"❌ All parsers failed: {e2}")
                    break

            # Extract match data from current page
            page_matches = extract_match_data(soup)
            all_matches.extend(page_matches)
            # print(
            #     f"📊 Extracted {len(page_matches)} matches from page {page_count}")

            # Check if there are more pages
            if not check_and_navigate_pagination(driver):
                break

            page_count += 1

            # Safety limit to prevent infinite loops
            if page_count > 50:  # Reasonable limit
                print("⚠️ Reached page limit, stopping pagination")
                break

        driver.quit()
        print(
            f"🏆 Total match results extracted from yesterday: {len(all_matches)}")
        return all_matches

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if 'driver' in locals():
            driver.quit()
        return []


def update_alerts_with_final_scores():
    """
    Creates a copy of alerts_log.csv and updates it with final scores from results.csv
    Matches records based on date and title

    Returns:
        str: Path to the updated file, or None if error
    """

    # Define file paths
    alerts_log_file = os.getenv('ALERT_LOG_FILE', 'alerts_log.csv')
    results_file = os.getenv('RESULT_LOG_FILE', 'results.csv')
    output_file = os.getenv('FINAL_DB_FILE', 'final_db.csv')

    # Create output filename with timestamp
    # current_time = datetime.now().strftime('%d-%m-%y-%H-%M-%S')
    # output_file = f"alerts_final_{current_time}.csv"

    try:
        # Load alerts_log.csv
        if not os.path.exists(alerts_log_file):
            print(f"❌ {alerts_log_file} not found")
            return None

        alerts_df = pd.read_csv(alerts_log_file, quoting=0, escapechar='\\')

        # Load results.csv
        if not os.path.exists(results_file):
            print(f"❌ {results_file} not found")
            return None

        results_df = pd.read_csv(results_file, quoting=0, escapechar='\\')

        # Add these columns to alerts_df if they don't exist, in the desired order
        if 'home_ft_goals' not in alerts_df.columns:
            alerts_df.insert(alerts_df.columns.get_loc('ht_goals') + 1, 'home_ft_goals', '')
        if 'away_ft_goals' not in alerts_df.columns:
            alerts_df.insert(alerts_df.columns.get_loc('home_ft_goals') + 1, 'away_ft_goals', '')
        if 'ft_goals' not in alerts_df.columns:
            alerts_df.insert(alerts_df.columns.get_loc('away_ft_goals') + 1, 'ft_goals', '')

        # Update alerts_df with home_ft_goals, away_ft_goals, and ft_goals from results_df
        matches_found = 0
        for idx, alert_row in alerts_df.iterrows():
            # Try to find matching row in results based on team names
            # Since results.csv uses home_team/away_team and alerts uses home-team/away-team
            matching_result = results_df[
                (results_df['home_team'] == alert_row['home-team']) &
                (results_df['away_team'] == alert_row['away-team'])
            ]

            if not matching_result.empty:
                result_row = matching_result.iloc[0]
                alerts_df.at[idx, 'home_ft_goals'] = result_row.get('home_ft_goals')
                alerts_df.at[idx, 'away_ft_goals'] = result_row.get('away_ft_goals')
                alerts_df.at[idx, 'ft_goals'] = result_row.get('ft_goals')
                matches_found += 1

        # return alerts_df
        # Save the updated dataframe to new file
        # alerts_df.to_csv(output_file, index=False, quoting=3, escapechar='\\')
        # alerts_df.to_csv(output_file, index=False, quoting=0, escapechar='\\')

        # print(
        #     f"📝 Created {output_file} with {matches_found} final scores updated")
        # return output_file
        # # Ensure goal columns are Int64 to maintain integer types
        # alerts_df['home_ft_goals'] = alerts_df['home_ft_goals'].astype('Int64')
        # alerts_df['away_ft_goals'] = alerts_df['away_ft_goals'].astype('Int64')
        # alerts_df['ft_goals'] = alerts_df['ft_goals'].astype('Int64')

        # Append updated records to final_db.csv
        success, num_appended = append_to_csv(alerts_df.to_dict('records'), output_file)
        if success:
            print(f"📝 Appended {num_appended} updated records with final scores to {output_file}")
            return output_file
        else:
            print(f"❌ Failed to append updated records to {output_file}")
            return None

    except Exception as e:
        print(f"❌ Error creating final scores file: {e}")
        return None


def backfill_tournament_and_odds():
    """
    Backfills existing alerts_log.csv records with tournament and odds data from today.csv
    Updates records where tournament data is missing

    Returns:
        int: Number of records updated
    """

    # Define file paths
    alerts_log_file = os.getenv('ALERT_LOG_FILE', 'alerts_log.csv')
    today_csv = os.getenv('REMOTE_TODAY_FILE', 'today.csv')

    try:
        # Load both files
        if not os.path.exists(alerts_log_file):
            print(f"❌ {alerts_log_file} not found")
            return 0

        if not os.path.exists(today_csv):
            print(f"❌ {today_csv} not found")
            return 0

        alerts_df = pd.read_csv(alerts_log_file, quoting=0, escapechar='\\')
        today_df = pd.read_csv(today_csv, quoting=0, escapechar='\\')

        # Add missing columns if they don't exist
        for col in ['tournament', 'pre-match_odds_home', 'pre-match_odds_draw', 'pre-match_odds_away']:
            if col not in alerts_df.columns:
                alerts_df[col] = ''

        # Update records
        updates_made = 0
        for idx, alert_row in alerts_df.iterrows():
            # Only update if tournament is empty or missing
            if pd.isna(alert_row.get('tournament')) or alert_row.get('tournament') == '':
                # Find matching record in today.csv
                matching_row = today_df[
                    (today_df['date'] == alert_row['date']) &
                    (today_df['title'] == alert_row['title'])
                ]

                if not matching_row.empty:
                    match = matching_row.iloc[0]
                    alerts_df.at[idx, 'tournament'] = match.get(
                        'tournament', '')
                    alerts_df.at[idx, 'pre-match_odds_home'] = match.get(
                        'pre-match_odds_home', '')
                    alerts_df.at[idx, 'pre-match_odds_draw'] = match.get(
                        'pre-match_odds_draw', '')
                    alerts_df.at[idx, 'pre-match_odds_away'] = match.get(
                        'pre-match_odds_away', '')
                    updates_made += 1

        # Save updated file
        if updates_made > 0:
            # alerts_df.to_csv(alerts_log_file, index=False,
            #                  quoting=3, escapechar='\\')
            alerts_df.to_csv(alerts_log_file, index=False,
                             quoting=0)
            print(
                f"📝 Backfilled {updates_made} records with tournament and odds data")
        else:
            print("📝 No records needed backfilling")

        return updates_made

    except Exception as e:
        print(f"❌ Error backfilling data: {e}")
        return 0
