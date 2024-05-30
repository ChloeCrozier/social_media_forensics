"""Functions that can be used to gauge suspiciousness of edits and users."""

import pywikibot as pwb
from functools import lru_cache

def is_anon(edit):
    """Returns whether an edit was made anonymously.

    Args:
        edit (dict): The dict representing the edit.

    Returns:
        bool: Whether the edit was made anonymously.
    """
    return edit['userid'] == 0

# Not sure how useful this one is, just made it as an easy test
def no_comment(edit):
    """Returns whether an edit was made with an empty comment and a change in byte size of at least 10.

    Args:
        edit (dict): The dict representing the edit.

    Returns:
        bool: Whether the edit was made with an empty comment and a change in byte size of at least 10.
    """
    return edit['comment'] == "" and abs(edit['size_delta']) > 10

def young(edit):
    """Returns whether the author of an edit registered in the past 100 days.

    Args:
        edit (dict): The dict representing the edit.

    Returns:
        bool: Whether the edit was posted by an account younger than 100 days.
    """
    # Registration date cannot be found for anonymous users
    if edit['userid'] == 0:
        return False
    else: return __young_internal(edit['user'])


def few_posts(edit):
    """Returns whether the author of an edit has posted fewer than 10 edits.

    Args:
        edit (dict): The dict representing the edit.

    Returns:
        bool: Whether the edit was posted by an account with fewer than 10 edits.
    """
    # Edit count cannot be found for anonymous users
    if edit['userid'] == 0:
        return False
    else: return __few_posts_internal(edit['user'])

# Section: Internal functions for metric functions that require API calls.
# A separate, internal function is needed because otherwise the caching feature would
# fail (different edits with same username -> no caching; same username repeatedly fed to
# internal function -> successful caching)

@lru_cache(128)
def __young_internal(username):
    user = pwb.User(default_site, username)
    if user:
        reg = user.registration()
        if reg:
            return (pwb.Timestamp.now() - reg).days < 100
    return False

@lru_cache(128)
def __few_posts_internal(username):
    user = pwb.User(default_site, username)
    if user:
        return user.editCount() <= 10

# TODO: When creating metrics where the API must be queried, use
# functools's caching features to speed up retrieval
# e.g. checking information about a user: the return value will always be the
# same for the same username, so we can lru_cache the result

metrics = {
    "anon": is_anon,
    "no_comment": no_comment,
    "young": young,
    "few_posts": few_posts
}

# The site used in metric function calls, since a site can't be passed as a parameter
default_site = pwb.Site("en", "wikipedia")