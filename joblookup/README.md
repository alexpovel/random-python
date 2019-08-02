# Lookup of job openings

Script visits a website using Selenium (we need JavaScript capabilities) and returns the found HTML source.
It is cleaned up using BeautifulSoup and then a regex looks for the number of open positions we are interested in.
The specific URL is supplied from a text file.
For reasons of privacy, it is not part of this repository.
Alternatively, supply the script with one argument in the command line.

The script logs all previous job searches.
If a log exists, it extracts the number of open positions found from the last entry.
Should the current number of openings exceed the previous one, a notification of high urgency is put out.
Otherwise, the same notification on a normal level of urgency is shown.
These notifications work for Gnome desktops (tested on Ubuntu 19.04).
