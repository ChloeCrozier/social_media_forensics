"""Checks suspiciousness of pages."""

from get_edits import get_edits
import pandas as pd
from statistics import stdev
import pywikibot as pwb
import wikibot_extensions
from pprint import pprint
from sus_metrics import metrics as suspiciousness_metrics # renamed to avoid variable overwriting

# TODO: Add functionality to check suspiciousness of users that make the edits

# TODO: This function can probably be abstracted to handle outliers of any type, not just edits
def find_outliers(sus_stats: pd.DataFrame, sus_metrics: dict, sus_marker: float = 2) -> dict:
    """Finds pages with suspicious edits by comparing various suspicious metrics against the average for similar pages.

    Args:
        sus_stats (pandas.DataFrame): The dataset to be analyzed for outliers, where rows are pages
            and columns are the metrics.
        sus_metrics (dict): The metrics to judge the pages by.
        sus_marker (float, optional): The number of standard deviations a page must be
            from the mean to qualify as suspicious. Defaults to 2.

    Returns:
        dict: The 2-layer dict containing each suspicious page, with the metric and then the page title as keys.
    """
    # Constructs the outliers dict with the following format:
    # {metric1: {page1: suspiciousness, page2: suspiciousness}, metric2: {page1: suspiciousness, page2: suspiciousness}, etc}
    # Uses dictionary comprehension to create a dictionary entry for each metric
    # For each metric, create another dictionary containing each page along with the page's suspiciousness if the
    # suspiciousness exceeds the specified limit
    outliers = {
        metric: {
            cell[0]: cell[1] for cell in sus_stats[metric].items() if cell[1] < -sus_marker or cell[1] > sus_marker
        } 
        for metric in sus_metrics
    }

    return outliers

def find_suspicious_users(sus_edits: dict, sus_stats: dict, sus_metrics: dict) -> dict:
    """Finds suspicious users given stats on pages' suspiciousness and the edits on those pages.

    Args:
        sus_edits (dict): The edits made on suspicious pages.
        sus_stats (dict): The suspiciousness stats of the pages.
        sus_metrics (dict): The metrics used to rate edits' suspiciousness.

    Returns:
        dict: Suspicious users in each metric.
    """
    sus_users_dict = {}
    # For each metric,
    for metric_name in sus_metrics:
        # Initialize a set of users
        sus_users_dict[metric_name] = set()
        # For each page with suspicious edits,
        for page_name, page in sus_edits[metric_name].items():
            # If the page is a suspicious outlier,
            if page_name in sus_stats[metric_name]:
                # Add the page's edits' users to the suspicious users for that metric
                for edit in page:
                    sus_users_dict[metric_name].add(edit["user"])

    return sus_users_dict

def search_wiki(site, search_term: str, max_pages: int) -> list:
    """Searches a site using a search term, returning up to the specified number of page titles.

    Args:
        site (pywikibot.APISite): The site to search.
        search_term (str): The search term.
        max_pages (int): The max number of pages to return.

    Returns:
        list: The list of string titles found by the search.
    """
    return [p.title() for p in site.search(search_term, total = max_pages)]

def get_pages_suspiciousness(titles: list, site: pwb.APISite, sus_metrics: dict, min_edits: int = 0,
        start_month: pwb.Timestamp = None, end_month: pwb.Timestamp = None, 
        get_sus_edits: bool = False) -> "pd.DataFrame | tuple":
    """Gets a DataFrame representing the suspiciousness of each edit set according to each provided metric.

    If the start_month and end_month are both specified, the edit sets will be each page-month. If either
    are not specified, the edit sets will be each page.

    Args:
        titles (list): The list of string titles to get the suspiciousness of.
        site (pywikibot.APISite): The site containing the pages.
        sus_metrics (dict): The metrics to judge each page's suspiciousness,
            in the format {metric_name: metric_function}
        min_edits (int, optional): The minimum number of edits required for a page or page-month to be 
            included in suspiciousness checking.
        start_month (pywikibot.Timestamp, optional): The month to start recording edits.
        end_month (pywikibot.Timestamp, optional): The month to end recording edits. If either start_month
            or end_month is None, both will be disregarded and all pages' full edit history will be recorded.
        get_sus_edits (bool, optional): Whether to additionally return the edits marked
            suspicious by the provided metric.

    Returns:
        pandas.DataFrame: A DataFrame representing each edit set's suspiciousness. Columns represent the 
            suspiciousness metrics and rows represent each edit set.
        or, if get_sus_edits, tuple: the above suspiciousness DataFrame,
            the edits matching each metric by page.
    """
    page_stats = pd.DataFrame()

    # Get dict of pages' edit dicts
    edit_dicts = {}
    if start_month is None or end_month is None:
        # Get the edit dict for each page if there are enough to meet the minimum
        for title in titles:
            edits = get_edits(title, site)
            if len(edits) >= min_edits:
                edit_dicts[title] = edits
        
        # Make the row names equal the page titles
        page_stats.index = edit_dicts.keys()
    else:
        # Get the months
        month_sets = wikibot_extensions.get_months_between(start_month, end_month)
        # Assign the page-month titles e.g. "Title1 2022-04"
        page_months = wikibot_extensions.get_titles_months(titles, month_sets)

        for title, month_set in page_months.items():
            # Get the edit dicts for each page-month if there are enough to meet the minimum
            edits = get_edits(title[:-8], site, start_time=month_set[0], end_time=month_set[1])
            if len(edits) >= min_edits:
                edit_dicts[title] = edits

        # Make the row names equal the page-month strings
        page_stats.index = edit_dicts.keys()

    if get_sus_edits:
        sus_edits = {}

    # For each suspiciousness metric,
    for metric_name, metric_func in sus_metrics.items():
        # Calculate the percent of edits that are suspicious according to this 
        # metric for each page along with the avg and SD of the percent for all pages
        result = get_suspicious_statistics(edit_dicts, metric_func, get_sus_edits=get_sus_edits)
        edit_sus_percents, avg, sd = result[0:3]
        # Get suspicious edits if specified by user
        if get_sus_edits:
            sus_edits[metric_name] = result[3]
        # For this metric, set each page's suspiciousness as the number of SDs from the mean
        page_stats[metric_name] = [(percent - avg) / sd for _, percent in edit_sus_percents.items()]

    if get_sus_edits:
        return page_stats, sus_edits
    else:
        return page_stats

def get_suspicious_statistics(edit_dicts: dict, metric, get_sus_edits: bool = False) -> tuple:
    """Gets the suspiciousness of each page evaluated by the specified metric.

    Args:
        edit_dicts (dict): The dict containing the page names as keys and the 
            list of each page's edits as values.
        metric (function): The function to evaluate each edit by.
        get_sus_edits (bool, optional): Whether to additionally return the edits marked
            suspicious by the provided metric.

    Returns:
        tuple: The dict representing the percent of each page's edits that met the metric,
            the average percent of all page's edits that met the metric, 
            and the standard deviation of the pages' metric percents,
            (optional, dependent on parameter get_sus_edits) edits matching the metric by page.
    """
    # The percent of each page's edits that meet the specified metric
    percent_suspicious = {}

    if get_sus_edits:
        sus_edits = {}

    for page_name, edit_list in edit_dicts.items():
        if len(edit_list) == 0:
            percent_suspicious[page_name] = 0
        else:
            # Create list of 1s and 0s, 1s representing edits that meet the specified
            # suspicious edits criteria
            sus_edits_binary = [int(metric(edit)) for edit in edit_list]

            # Record suspicious edits if the user requested
            if get_sus_edits:
                sus_edits[page_name] = [edit for i, edit in enumerate(edit_list) if sus_edits_binary[i]]

            # Use the suspicious edits list to determine the percent of edits on this page
            # that were made suspiciously (i.e. that meet the metric)
            percent_suspicious[page_name] = sum(sus_edits_binary) / len(sus_edits_binary)

    # Create temp list from the {page: percent} dictionary for easy calculation
    percents_list = [percent for _, percent in percent_suspicious.items()]
    # Calculate average and SD for this metric
    average = sum(percents_list) / len(percents_list)
    sd = stdev(percents_list)

    # If the sd is 0 (all percents are the same), we can set it
    # to 1 so that when we divide by SD the result will be 0 still
    # but we won't get a ZeroDivisionError.
    if sd == 0:
        sd = 1

    if get_sus_edits:
        return percent_suspicious, average, sd, sus_edits
    else:
        return percent_suspicious, average, sd

# Example of how to find outliers in a search for the given metrics
def main():
    search = '"Joe Biden" incategory:living_people'
    # SDs from mean that qualifies as sus
    suspicious_marker = 2
    # number of pages to get from search
    max_pages = 5
    # min edits an edit set must have to be considered
    min_edits = 10

    site = pwb.Site("en", "wikipedia")

    # Gets the titles retrieved from the search
    titles = search_wiki(site, search, max_pages)

    print("Found pages:", titles)

    # Arbitrary testing months
    start_month = pwb.Timestamp(2021, 10, 1)
    end_month = pwb.Timestamp(2021, 12, 1)

    # Find the time taken to calculate outliers
    stopwatch = False
    if stopwatch:
        import time
        start = time.perf_counter()

    # Gets the DF for the suspiciousness level of each page for each metric
    sus_stats, sus_edits = get_pages_suspiciousness(titles, site, suspiciousness_metrics,
        min_edits=min_edits, start_month=start_month, end_month=end_month, get_sus_edits=True)

    # Find outliers in the suspiciousness stats
    stats = find_outliers(sus_stats, suspiciousness_metrics, suspicious_marker)

    if stopwatch:
        print("Time to get edits: ", time.perf_counter() - start)

    # Display suspicious pages
    print("\nSuspicious pages by metric:")
    pprint(stats)

    # Find suspicious users
    sus_users_dict = find_suspicious_users(sus_edits, stats, suspiciousness_metrics)

    # Display suspicious users by metric
    print("\nSuspicious users by metric:")
    pprint(sus_users_dict)

    # Condense suspicious users into a single list
    sus_users_list = [user for _, users in sus_users_dict.items() for user in users]

    # Display list of suspicious users
    print("\nAll suspicious users:")
    print(sus_users_list)

if __name__ == "__main__":
    main()