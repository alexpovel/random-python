#! /usr/bin/python3
import time
import re
import datetime
import sys
import notify2

from bs4 import BeautifulSoup
# Selenium requires geckodriver, cf. https://stackoverflow.com/q/40208051/11477374
from selenium import webdriver
from selenium.webdriver.firefox.options import Options


# Keep URL a secret and import it, or take from argument
try:
    URL = sys.argv[1]
    print("Scraping supplied URL:", URL)
except IndexError:
    with open("url.txt", "r") as url_file:
        URL = url_file.readline()
    print("No URL supplied as CL argument, using default:", URL)

options = Options()
options.headless = True  # Do not open window/display

# Use Selenium to have JavaScript support
driver = webdriver.Firefox(options=options)
driver.get(URL)
time.sleep(5)  # Give it time to actually load
html_source = driver.page_source  # Extract source code
# Make it slightly more readable
html_text = BeautifulSoup(html_source, "html.parser").text

with open("jobsite.log", "w") as text_file:
    text_file.write(html_text)

match = re.search(r"(\d+)\svon\s\d+\sStellenangebote", html_text)
if match:
    number_of_jobs = match.group(1)
    base_message = "Found " + str(number_of_jobs) + " jobs for: " + URL
    with open("jobsearches.log", "a") as log_file:
        log_file.write(
            str(datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")) + " " +
            base_message + "\n")
else:
    print("No match found in supplied URL", URL)

notify2.init("Job Search Script")
notification = notify2.Notification("Job Search", base_message, "applications-science")
notification.show()
