"""Pull live event data and return summary."""


from datetime import datetime
from utils import scrape_sb_live, update_alert_log, generate_stats_prompts


# Scrape fresh data
matches_data = scrape_sb_live()

# Save to file
update_alert_log(matches_data)

# Generate stats prompt
stats_prompt = generate_stats_prompts(
    matches_data, output_file='stats_prompt.txt')
