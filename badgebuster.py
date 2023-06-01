from __future__ import annotations

import html
import ssl
import sys
from html.parser import HTMLParser
from http.client import HTTPSConnection
from urllib.parse import urlparse

from urllib.request import urlopen


def retrieve_readme_html(repo_uri: str) -> str:
    full_url = f"https://github.com/{repo_uri}/blob/master/README.md"
    with urlopen(full_url) as response:
        return response.read().decode("utf-8")


class ReadmeParser(html.parser.HTMLParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.badge_links = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        super().handle_starttag(tag, attrs)

        if tag != "img":
            return

        cached_badge_link = None
        source_link = None

        for attr in attrs:
            if attr[0] == "src" and attr[1].startswith(
                "https://camo.githubusercontent.com/"
            ):
                cached_badge_link = attr[1]

            if attr[0] == "data-canonical-src":
                source_link = attr[1]

        if cached_badge_link and source_link:
            self.badge_links.append((cached_badge_link, source_link))


def extract_badge_links(readme_html: str) -> list[str]:
    parser = ReadmeParser()
    parser.feed(readme_html)
    parser.close()

    return parser.badge_links


def bust_image_cache(link: str) -> bool:
    schema, netloc, url, params, query, fragments = urlparse(link)

    connection = HTTPSConnection(netloc, context=ssl.create_default_context())
    connection.connect()

    connection.putrequest("PURGE", url)
    connection.endheaders()

    r = connection.getresponse()
    return r.status == 200


def is_bustable_link(link: str) -> bool:
    _schema, _netloc, _url, _params, query, _fragments = urlparse(link)
    return "bogus-cache-buster" in query


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 badgebuster.py <REPO_URI>")
        sys.exit(1)

    repo_uri = sys.argv[1]
    print("Scanning repo: " + repo_uri)

    readme_html = retrieve_readme_html(repo_uri)
    badge_links = extract_badge_links(readme_html)

    for cached_link, source_link in badge_links:
        if not is_bustable_link(source_link):
            continue

        print(f"Busting image cache for: {source_link}")
        bust_image_cache(cached_link)

    print("Done!")


if __name__ == "__main__":
    main()
