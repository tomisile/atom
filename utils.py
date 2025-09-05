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
        print(f"Found {len(matches)} ongoing events")

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
                    driver.quit()
                    return []

        # Find all matches with the correct class structure
        matches = soup.find_all(
            'div', class_='m-table-row m-content-row match-row')
        print(f"There are {len(matches)} more upcoming events today")

        extracted_data = []

        for match in matches:
            try:
                left_team_cell = match.find(
                    class_='m-table-cell left-team-cell')

                if left_team_cell:
                    left_team_table = left_team_cell.find(
                        class_='left-team-table')
                    if left_team_table:
                        game_id_elem = left_team_table.find(class_='game-id')
                        if game_id_elem:
                            game_id_text = game_id_elem.get_text(strip=True)
                            # Extract 5-digit number using regex
                            game_id_match = re.search(
                                r'\b\d{5}\b', game_id_text)
                            # if game_id_match:
                            #     match_data['game_id'] = game_id_match.group()
                            # else:
                            #     match_data['game_id'] = game_id_text  # Fallback to full text if no 5-digit found

                        # Extract time
                        time_elem = left_team_table.find(class_='clock-time')
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

                match_data = {
                    'time': time_text,
                    'title': title,
                    'game-id': game_id_match.group() if game_id_match else game_id_text,
                    'home-team': home_team,
                    'away-team': away_team,
                }
                extracted_data.append(match_data)

            except Exception as e:
                print(f"⚠️ Error processing match: {e}")
                continue

        driver.quit()  # Clean up browser session

        # Convert extracted_data to DataFrame for top 5 kick-off times
        df = pd.DataFrame(extracted_data)
        if not df.empty and 'time' in df.columns:
            top_times = df['time'].value_counts().head(5)
            print(f"\n⏱️ Top 5 kick-off time:")
            for time, count in top_times.items():
                print(f"  - {count} events at {time}.")
        else:
            print(f"\n⏱️ Top 5 kick-off time: No data available")

        return extracted_data

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
        filename = f"sb_data_{current_time.strftime('%d-%m-%y-%H-%M-%S')}.csv"

    try:
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        print(f"💾 Data saved to {filename}")
        return True, filename
    except Exception as e:
        print(f"❌ Error saving to CSV: {e}")
        return False, None


def update_alert_log(extracted_data):
    """
    Updates alerts_log.csv with new match data while avoiding duplicates

    Args:
        extracted_data (list): List of dictionaries containing match data from scrape_sb_live()

    Returns:
        int: Number of new records added
    """

    # Define the CSV file path
    csv_file = 'alerts_log.csv'

    # Get current date and time
    current_date = datetime.now().strftime('%d-%m-%y')
    current_time = datetime.now().strftime('%H:%M')

    # Check if extracted_data is empty
    if not extracted_data:
        # print("📝 No new data to add to alerts log.")
        return 0

    # Prepare new data with additional columns
    new_records = []
    for match in extracted_data:
        new_record = {
            'date': current_date,
            'log_time': current_time,
            'title': match['title'],
            'home-team': match['home-team'],
            'away-team': match['away-team'],
            'ht_goals': match['ht_goals'],
            'criteria_met': 'unknown',
            'ft_goals': 'unknown'
        }
        new_records.append(new_record)

    # Create DataFrame from new records
    new_df = pd.DataFrame(new_records)

    try:
        # Check if the CSV file exists
        if os.path.exists(csv_file):
            # Load existing data
            existing_df = pd.read_csv(csv_file)

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
                updated_df.to_csv(csv_file, index=False)

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
            new_df.to_csv(csv_file, index=False)
            # print(f"📝 Created new alerts_log.csv with {len(new_records)} records")
            return len(new_records)

    except Exception as e:
        # print(f"❌ Error updating alerts_log.csv: {e}")
        return 0


def generate_stats_prompts(extracted_data, output_file='stats_prompts.txt'):
    """
    Generates statistical analysis prompts for each match in extracted_data
    and saves them to a text file for easy copy/paste

    Args:
        extracted_data (list): List of dictionaries containing match data from scrape_sb_live()
        output_file (str): Name of the output text file (default: 'stats_prompts.txt')

    Returns:
        int: Number of prompts generated
    """

    # Check if extracted_data is empty
    if not extracted_data:
        print("📝 No matches found - no prompts to generate.")
        return 0

    # Get current date for the prompts (format: YYYY-MM-DD)
    current_date = datetime.now().strftime('%Y-%m-%d')

    # Prompt template
    prompt_template = """Provide the following stats for the last 5 matches of both teams in the football match {home_team} vs {away_team} played on {date} (format: YYYY-MM-DD):
* Average number of goals scored by {home_team} in the last 5 matches
* Average number of goals conceded by {home_team} in the last 5 matches
* Total number of goals scored by {home_team} in the last 5 matches
* Total number of goals conceded by {home_team} in the last 5 matches
* Total season stats for {home_team} (games played, games won, games drawn, games lost, goals scored and conceded, if available)
* Average number of goals scored by {away_team} in the last 5 matches
* Average number of goals conceded by {away_team} in the last 5 matches
* Total number of goals scored by {away_team} in the last 5 matches
* Total number of goals conceded by {away_team} in the last 5 matches
* Total season stats for {away_team} (games played, games won, games drawn, games lost, goals scored and conceded, if available)
Provide live stats (shots on target, off target, corners) for {home_team} vs {away_team} on {date}. 
Calculate over 0.5 goals probability using Poisson model from last 5 match averages.
List only these stats for each team, in this order, with no additional text. Use 'N/A' if data is unavailable."""

    try:
        # Generate prompts for all matches
        all_prompts = []

        for i, match in enumerate(extracted_data, 1):
            home_team = match['home-team']
            away_team = match['away-team']

            # Generate the prompt for this match
            prompt = prompt_template.format(
                home_team=home_team,
                away_team=away_team,
                date=current_date
            )

            # Add separator and match info for clarity
            match_header = f"\n{'='*80}\nMATCH {i}: {home_team} vs {away_team} (0 goals at HT)\n{'='*80}\n"
            full_prompt = match_header + prompt

            all_prompts.append(full_prompt)

        # Write all prompts to file
        with open(output_file, 'w', encoding='utf-8') as f:
            # Add file header with timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            file_header = f"FOOTBALL STATS PROMPTS - Generated on {timestamp}\n"
            file_header += f"Total matches: {len(extracted_data)}\n"
            file_header += "="*80 + "\n"

            f.write(file_header)

            # Write all prompts
            for prompt in all_prompts:
                f.write(prompt)
                f.write("\n\n")  # Add spacing between prompts

            # Add footer
            footer = f"\n{'='*80}\nEND OF PROMPTS - {len(extracted_data)} matches total\n{'='*80}"
            f.write(footer)

        # print(f"📝 Generated {len(extracted_data)} stat prompts and saved to '{output_file}'")
        # print(f"💾 File size: {os.path.getsize(output_file)} bytes")

        return len(extracted_data)

    except Exception as e:
        print(f"❌ Error generating prompts: {e}")
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
