"""Google search command for Autogpt."""
from __future__ import annotations

import json
import time
from itertools import islice
from typing import TYPE_CHECKING

from duckduckgo_search import DDGS

from autogpt.commands.command import command

if TYPE_CHECKING:
    from autogpt.config import Config

DUCKDUCKGO_MAX_ATTEMPTS = 3


@command(
    "google",
    "Google Search",
    '"query": "<query>"',
    lambda config: not config.google_api_key,
)
def google_search(query: str, config: Config, num_results: int = 8) -> str:
    """Return the results of a Google search

    Args:
        query (str): The search query.
        num_results (int): The number of results to return.

    Returns:
        str: The results of the search.
    """
    search_results = []
    attempts = 0

    while attempts < DUCKDUCKGO_MAX_ATTEMPTS:
        if not query:
            return json.dumps(search_results)

        results = DDGS().text(query)
        search_results = list(islice(results, num_results))

        if search_results:
            break

        time.sleep(1)
        attempts += 1

    results = json.dumps(search_results, ensure_ascii=False, indent=4)
    return safe_google_results(results)


@command(
    "google",
    "Google Search",
    '"query": "<query>"',
    lambda config: bool(config.google_api_key) and bool(config.custom_search_engine_id),
    "Configure google_api_key and custom_search_engine_id.",
)
def google_official_search(
    query: str, config: Config, num_results: int = 8
) -> str | list[str]:
    """Return the results of a Google search using the official Google API

    Args:
        query (str): The search query.
        num_results (int): The number of results to return.

    Returns:
        str: The results of the search.
    """

    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    try:
        # Get the Google API key and Custom Search Engine ID from the config file
        api_key = config.google_api_key
        custom_search_engine_id = config.custom_search_engine_id

        # Initialize the Custom Search API service
        service = build("customsearch", "v1", developerKey=api_key)

        # Send the search query and retrieve the results
        result = (
            service.cse()
            .list(q=query, cx=custom_search_engine_id, num=num_results)
            .execute()
        )

        # Extract the search result items from the response
        search_results = result.get("items", [])

        # Create a list of only the URLs from the search results
        search_results_links = [item["link"] for item in search_results]

    except HttpError as e:
        # Handle errors in the API call
        error_details = json.loads(e.content.decode())

        # Check if the error is related to an invalid or missing API key
        if error_details.get("error", {}).get(
            "code"
        ) == 403 and "invalid API key" in error_details.get("error", {}).get(
            "message", ""
        ):
            return "Error: The provided Google API key is invalid or missing."
        else:
            return f"Error: {e}"
    # google_result can be a list or a string depending on the search results

    # Return the list of search result URLs
    return safe_google_results(search_results_links)


def safe_google_results(results: str | list) -> str:
    """
        Return the results of a google search in a safe format.

    Args:
        results (str | list): The search results.

    Returns:
        str: The results of the search.
    """
    return (
        json.dumps(
            [
                result.encode("utf-8", "ignore").decode("utf-8")
                for result in results
            ]
        )
        if isinstance(results, list)
        else results.encode("utf-8", "ignore").decode("utf-8")
    )
