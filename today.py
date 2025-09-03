"""Pull upcoming event data and analyse stats."""


from utils import scrape_sb_today, save_to_csv


# Scrape fresh data
matches_data = scrape_sb_today()

# Save to csv file
# events_today = save_to_csv(matches_data, "today.csv")

# Save watchlist events to separate csv file
# watchlist_events = save_to_csv(matches_data, "watchlist_today.csv")
