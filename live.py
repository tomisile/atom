"""Pull live event data and return summary."""


from utils import scrape_sb_live


# Scrape fresh data
matches_data = scrape_sb_live()
