"""Pull live event data and return summary."""


from datetime import datetime, timedelta
import os
from utils import scrape_sb_results, save_to_csv, update_alerts_with_final_scores

# Get current date
current_date = datetime.now()
current_date_str = current_date.strftime('%d/%m/%Y')

# Get previous day
previous_day = current_date - timedelta(days=1)
previous_day_str = previous_day.strftime('%d/%m/%Y')

print(f"Current date: {current_date_str}")
print(f"Previous day: {previous_day_str}")

# Scrape results from the previous day
results = scrape_sb_results(previous_day_str)

# Save to file
csv_file = os.getenv('RESULT_LOG_FILE', 'results.csv')
save_to_csv(results, csv_file)

# Save to file
# update_alerts_with_final_scores()
