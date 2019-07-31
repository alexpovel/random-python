#! /usr/bin/python3
import datetime
import os
import re
import sys
import time

import notify2
from bs4 import BeautifulSoup
# Selenium requires geckodriver, cf. https://stackoverflow.com/q/40208051/11477374
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

# Assemble path so script can be called from outside its location via symlink
base_dir = os.path.dirname(os.path.realpath(__file__))

# Assemble filepaths to lie in current base directory of the base script
filepaths = {
    # Keep URL a secret and import it
    "url": os.path.join(base_dir, "url.txt"),
    # The website content itself, for debugging
    "website": os.path.join(base_dir, "webcontent.log"),
    "searches": os.path.join(base_dir, "jobsearches.log")  # Previous searches
}

# Provide ability to get URL from command line argument
try:
    # Scrape using the supplied URL
    url = sys.argv[1]
except IndexError:
    # Scrape using the default from the URL file
    with open(filepaths["url"], "r") as url_file:
        url = url_file.readline()

options = Options()
options.headless = True  # Do not open window/display

# Use Selenium to have JavaScript support
driver = webdriver.Firefox(options=options)
driver.get(url)
time.sleep(5)  # Give it time to actually load
html_source = driver.page_source  # Extract source code
# Make it slightly more readable
html_text = BeautifulSoup(html_source, "html.parser").text

# Store a log for debugging the website content
with open("jobsite.log", "w") as text_file:
    text_file.write(html_text)

match = re.search(r"(\d+)\svon\s\d+\sStellenangebote", html_text)

if match:
    number_of_jobs = int(match.group(1))
    base_message = "Found " + str(number_of_jobs) + " jobs for: " + url

    notify2.init("Job Search Script")
    notification = notify2.Notification("Job Search",
                                        base_message,
                                        # Displayed icon
                                        # https://specifications.freedesktop.org/icon-naming-spec/latest/ar01s04.html
                                        "applications-science"
                                        )

    # The purpose of this try/except block is to see whether a log file exists from previous runs.
    # If so, get its last line and extract the number of jobs hit we got there.
    # The end goal is to increase the notification's urgency to CRITICAL if the number increased, aka a new job was listed.
    if os.path.isfile(filepaths["searches"]):
        with open(filepaths["searches"], "r") as logfile:
            current_line = 0
            for line in logfile:
                if line.strip():  # Ignore whitespace/empty lines
                    current_line = line
            last_line = current_line

            prev_search_match = re.search(r"Found\s(\d+)\s", last_line)
            prev_number_of_jobs = int(prev_search_match.group(1))
            if number_of_jobs > prev_number_of_jobs:
                # 0, 1, 2 for low, normal, critical
                # Critical notifications do not expire
                # https://people.gnome.org/~mccann/docs/notification-spec/notification-spec-latest.html#urgency-levels
                notification.set_urgency(2)

    # Finally, log what we have done with a timestamp
    with open(filepaths["searches"], "a") as logfile:
        logfile.write(str(datetime.datetime.now().strftime(
            "[%Y-%m-%d %H:%M:%S] ")) + base_message)

    notification.show()
