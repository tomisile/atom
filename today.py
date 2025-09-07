"""Pull upcoming event data and analyse stats."""


import os
from utils import scrape_sb_today, save_to_csv


# Scrape fresh data
matches_data = scrape_sb_today()


# Save to csv file
csv_file = os.getenv('REMOTE_TODAY_FILE', 'today.csv')
events_today = save_to_csv(matches_data, csv_file)

# Save watchlist events to separate csv file
# watchlist_events = save_to_csv(matches_data, "watchlist_today.csv")
