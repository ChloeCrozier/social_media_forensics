# Example code for how to search wikipedia and sort the results by pageview.

import pywikibot as pwb
from wikibot_extensions import get_pageviews_unlimited

# Guide to search terms and parameters: https://www.mediawiki.org/wiki/Help:CirrusSearch
search_term = "American \"chief of staff\" incategory:living_people"
num_to_find = 30

site = pwb.Site("en", "wikipedia")

# This function gets the specified number of pages with the highest relevance to the topic and
# returns them sorted alphabetically.
result = list(site.search(search_term, total = num_to_find))

# Get just the list of titles without sorting by pageviews
titles = [t.title().replace(' ', '_') for t in result]

print(f"    Pages found relevant to the search: {titles}")

# Get the pageviews for each page
views = get_pageviews_unlimited(site, search_results=result)

# Sorts the titles by pageview count
sorted_by_views = [p for p in sorted(views, key=views.get, reverse=True)]

# Prints the 10 pages with the highest pageviews
print(f"    Top 10 pages by views: {sorted_by_views[:10]}")