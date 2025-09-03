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

                # Only include matches with 0 total goals at HT
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

            except Exception as e:
                print(f"⚠️ Error processing match: {e}")
                continue

        # print(f"\n📊 Summary:")
        # print(f"   - Total events found: {len(matches)}")
        print(
            f"   - HT: {halftime_matches}, H1: {first_half_matches}, H2: {second_half_matches}")
        print(f"   - 0 at HT: {zero_goal_matches}")

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


# def get_match_stats_soccerdata(home_team, away_team, league=None, season="2024-25"):
#     """
#     Extract match statistics using SoccerData library from multiple sources
#     Returns dictionary with comprehensive match stats
#     """
#     if not SOCCERDATA_AVAILABLE:
#         print("❌ SoccerData library not available")
#         return None

#     stats_data = {
#         'attempts_home': 0, 'attempts_away': 0,
#         'on_target_home': 0, 'on_target_away': 0,
#         'corners_home': 0, 'corners_away': 0,
#         'l5g_home_gf': 0, 'l5g_home_ga': 0,
#         'l5g_away_gf': 0, 'l5g_away_ga': 0,
#         'possession_home': 0, 'possession_away': 0,
#         'passes_home': 0, 'passes_away': 0,
#         'data_source': 'soccerdata'
#     }

#     try:
#         print(f"🔍 Using SoccerData for: {home_team} vs {away_team}")

#         # Try FotMob first (good for live match stats)
#         try:
#             fotmob = sd.FotMob()

#             # Search for recent matches involving these teams
#             home_matches = fotmob.read_team_match_stats(team=home_team, stat_type="match")
#             away_matches = fotmob.read_team_match_stats(team=away_team, stat_type="match")

#             # Find the match between these two teams
#             recent_match = None
#             if not home_matches.empty and not away_matches.empty:
#                 # Look for recent head-to-head match
#                 for idx, match in home_matches.iterrows():
#                     if away_team.lower() in str(match).lower():
#                         recent_match = match
#                         break

#             if recent_match is not None:
#                 # Extract basic stats (structure depends on FotMob data format)
#                 stats_data['attempts_home'] = getattr(recent_match, 'shots_home', 0) or 0
#                 stats_data['attempts_away'] = getattr(recent_match, 'shots_away', 0) or 0
#                 stats_data['on_target_home'] = getattr(recent_match, 'shots_on_target_home', 0) or 0
#                 stats_data['on_target_away'] = getattr(recent_match, 'shots_on_target_away', 0) or 0
#                 stats_data['corners_home'] = getattr(recent_match, 'corners_home', 0) or 0
#                 stats_data['corners_away'] = getattr(recent_match, 'corners_away', 0) or 0

#                 print("✅ Extracted stats from FotMob")
#                 return stats_data

#         except Exception as e:
#             print(f"⚠️ FotMob failed: {e}")

#         # Try SofaScore as fallback
#         try:
#             sofascore = sd.Sofascore()

#             # Get recent matches for both teams
#             home_stats = sofascore.read_team_match_stats(team=home_team)
#             away_stats = sofascore.read_team_match_stats(team=away_team)

#             # Process the data similar to FotMob
#             if not home_stats.empty or not away_stats.empty:
#                 print("✅ Extracted stats from SofaScore via SoccerData")
#                 return stats_data

#         except Exception as e:
#             print(f"⚠️ SofaScore failed: {e}")

#         # Try FBref for team statistics (season-long stats)
#         try:
#             fbref = sd.FBref()

#             # Get team stats for the season
#             if league:
#                 team_stats = fbref.read_team_season_stats(stat_type="standard")

#                 # Extract relevant team stats
#                 home_team_stats = team_stats[team_stats.index.get_level_values('team').str.contains(home_team, case=False, na=False)]
#                 away_team_stats = team_stats[team_stats.index.get_level_values('team').str.contains(away_team, case=False, na=False)]

#                 if not home_team_stats.empty and not away_team_stats.empty:
#                     # Extract season averages as proxy
#                     stats_data['l5g_home_gf'] = int(home_team_stats['goals_for'].iloc[0] / 5) if 'goals_for' in home_team_stats.columns else 0
#                     stats_data['l5g_home_ga'] = int(home_team_stats['goals_against'].iloc[0] / 5) if 'goals_against' in home_team_stats.columns else 0
#                     stats_data['l5g_away_gf'] = int(away_team_stats['goals_for'].iloc[0] / 5) if 'goals_for' in away_team_stats.columns else 0
#                     stats_data['l5g_away_ga'] = int(away_team_stats['goals_against'].iloc[0] / 5) if 'goals_against' in away_team_stats.columns else 0

#                     print("✅ Extracted stats from FBref")
#                     return stats_data

#         except Exception as e:
#             print(f"⚠️ FBref failed: {e}")

#         print("⚠️ No stats found via SoccerData")
#         return stats_data

#     except Exception as e:
#         print(f"❌ SoccerData extraction failed: {e}")
#         return stats_data


# def update_csv_with_soccerdata(csv_filename, league=None):
#     """
#     Update existing CSV file with SoccerData statistics (alternative to manual scraping)
#     """
#     if not SOCCERDATA_AVAILABLE:
#         print("❌ SoccerData library not available. Install with: pip install soccerdata")
#         return None

#     try:
#         # Read existing CSV
#         df = pd.read_csv(csv_filename)
#         print(f"📖 Reading {len(df)} matches from {csv_filename}")

#         # Add new columns if they don't exist
#         new_columns = ['attempts_home', 'attempts_away', 'on_target_home', 'on_target_away',
#                       'corners_home', 'corners_away', 'l5g_home_gf', 'l5g_home_ga',
#                       'l5g_away_gf', 'l5g_away_ga', 'possession_home', 'possession_away',
#                       'passes_home', 'passes_away', 'data_source']

#         for col in new_columns:
#             if col not in df.columns:
#                 df[col] = 0

#         # Process each match using SoccerData
#         for index, row in df.iterrows():
#             home_team = row['home-team']
#             away_team = row['away-team']
#             title = row['title']

#             print(f"🔍 Processing with SoccerData: {title}")

#             # Get stats using SoccerData
#             stats = get_match_stats_soccerdata(home_team, away_team, league)

#             if stats:
#                 # Update DataFrame with stats
#                 for stat_key, stat_value in stats.items():
#                     if stat_key in df.columns:
#                         df.at[index, stat_key] = stat_value

#                 print(f"✅ Updated stats for {title}")
#             else:
#                 print(f"⚠️ No stats found for {title}")

#             # Add delay to be respectful
#             time.sleep(1)

#         # Save updated CSV
#         updated_filename = csv_filename.replace('.csv', '_with_soccerdata.csv')
#         df.to_csv(updated_filename, index=False)

#         print(f"💾 Updated CSV saved as: {updated_filename}")
#         print(f"📊 Processed {len(df)} matches with SoccerData")

#         return updated_filename

#     except Exception as e:
#         print(f"❌ Error updating CSV with SoccerData: {e}")
#         return None

#     except Exception as e:
#         print(f"❌ Error searching Google for {match_title}: {e}")
#         return None


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
