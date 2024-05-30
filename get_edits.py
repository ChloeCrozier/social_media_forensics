"""Retrieves edits from a page."""

import pywikibot as pwb # pip install pywikibot "wikitextparser>=0.47.5"
import pywikibot.data.api as api
import pandas as pd
import datetime
from bs4 import BeautifulSoup
import threading

def get_edits(title, site, start_time=None, end_time=None, past_n_days=None, max_edits=None):
    """Gets the list of edits on a page, optionally between two timestamps.

    See get_edits_async for a description of the parameters.

    Returns:
        list: The list of the page's edits, sorted by most recent first.
    """
    return sorted(
        get_edits_async(title, site, start_time=start_time, end_time=end_time, 
            past_n_days=past_n_days, max_edits=max_edits),
        key=lambda edit: edit['timestamp'],
        reverse=True
    )

def get_edits_async(title, site, start_time=None, end_time=None, past_n_days=None, max_edits=None):
    """Gets the list of edits on a page asynchronously, optionally between two timestamps.

    Args:
        title (str): The title of the page.
        site (pywikibot.Site): The site object for the wiki.
        start_time (datetime.datetime): The start timestamp for the edits.
        end_time (datetime.datetime): The end timestamp for the edits.
        past_n_days (int): The number of days in the past to retrieve edits for.
        max_edits (int): The maximum number of edits to retrieve.

    Returns:
        list: The list of the page's edits, sorted by most recent first.
    """
    edits = []
    threads = []

    if past_n_days is not None and start_time is None:
        start_time = datetime.datetime.now() - datetime.timedelta(days=past_n_days)

    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "titles": title,
        "rvprop": "ids|timestamp|user|userid|comment|tags|size|flags",
        "rvlimit": "max"
    }
    if start_time:
        params["rvstart"] = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    if end_time:
        params["rvend"] = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    def get_revisions(params):
        req = api.Request(site, parameters=params)
        result = req.submit()
        if 'query' in result and 'pages' in result['query']:
            for page_id in result['query']['pages']:
                page = result['query']['pages'][page_id]
                if 'revisions' in page:
                    for rev in page['revisions']:
                        get_edit_dict(rev, site, edits)

    with ThreadPoolExecutor(max_workers=5) as executor:
        while True:
            params['rvcontinue'] = edits[-1]['revid'] if edits else 0
            thread = threading.Thread(target=get_revisions, args=(params,))
            threads.append(thread)
            thread.start()
            for t in threads:
                t.join()
            if len(edits) >= max_edits or 'continue' not in params:
                break

    return edits

def get_edit_dict(rev, site, edits):
    edit = {
        "revid": rev["revid"],
        "user": rev["user"],
        "userid": rev["userid"] if rev["user"] != "" else -1,
        "comment": rev["comment"] if "comment" in rev else "",
        "timestamp": rev["timestamp"],
        "tags": rev["tags"],
        "minor": "minor" in rev
    }
    add_diffs(edit, site)
    edits.append(edit)

def add_diffs(edit, site):
    req = api.Request(site, parameters={
        "action": "compare",
        "fromrev": edit["revid"],
        "torelative": "prev",
        "prop": "diff|size"
    })
    result = req.submit()
    compare = result["compare"]
    diff = compare["*"]
    soup = BeautifulSoup(diff, features="html.parser")
    added = []
    removed = []
    for tr in soup.find_all("tr"):
        added_line = tr.find("td", class_="diff-addedline")
        deleted_line = tr.find("td", class_="diff-deletedline")
        if added_line and deleted_line:
            added += [text.get_text() for text in added_line.find_all("ins")]
            removed += [text.get_text() for text in deleted_line.find_all("del")]
        elif added_line:
            div = added_line.find("div")
            if div:
                added.append(div.get_text())
        elif deleted_line:
            div = deleted_line.find("div")
            if div:
                removed.append(div.get_text())

    edit["added"] = added
    edit["removed"] = removed
    edit["new_size"] = compare["tosize"]
    edit["size_delta"] = compare["tosize"] - compare["fromsize"]

def get_edit_desc(edit):
    return "Edit by {user} ({userid}) at {timestamp}, size {new_size} ({size_delta}): \"{comment}\"".format(**edit)

def main():
    site = pwb.Site("en", "wikipedia")
    page = pwb.Page(site, "Hartley (surname)")

    edits = get_edits(page, site)

    df = pd.DataFrame(edits)
    pd.set_option("display.max_columns", None)

    df.to_csv("raw.csv")

if __name__ == "__main__":
    main()