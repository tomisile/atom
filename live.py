"""Pull live event data and return summary."""


from datetime import datetime
from utils import scrape_sb_live, update_alert_log, backfill_tournament_and_odds


# Scrape fresh data
matches_data = scrape_sb_live()

# Save to file
update_alert_log(matches_data)

backfill_tournament_and_odds()