# import requests
# from bs4 import BeautifulSoup
# import pandas as pd
# import time
# import re
# from urllib.parse import urljoin
# import csv
# from datetime import datetime

# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from webdriver_manager.chrome import ChromeDriverManager

from utils import scrape_sb_live

# SoccerData imports (install with: pip install soccerdata)
try:
    import soccerdata as sd
    SOCCERDATA_AVAILABLE = True
    # print("✅ SoccerData library available")
except ImportError:
    SOCCERDATA_AVAILABLE = False
    # print("⚠️ SoccerData library not installed. Run: pip install soccerdata")

# Scrape fresh data
matches_data = scrape_sb_live()
