from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote, quote_plus, unquote, urljoin, urlparse
from urllib.request import Request, urlopen


@dataclass(slots=True)
class WebResult:
    title: str
    url: str
    snippet: str
    text: str = ""
    source: str = "web"


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)


_QUESTION_WRAPPER = re.compile(r"^(qué|que)\s+(es|son)\b|^cómo\s+funciona\b|^como\s+funciona\b|^quién\s+(es|fue)\b|^quien\s+(es|fue)\b|^define\b|^dime\s+", re.I)
_LEADING_ARTICLES = re.compile(r"^(el|la|los|las|un|una|unos|unas)\s+", re.I)


def keywords_from(query: str) -> str:
    """Turn '¿Qué es un barco?' into 'barco' so title-search APIs match."""
    text = query.strip().strip("¿¡?!. ").strip()
    text = _QUESTION_WRAPPER.sub("", text, count=1).strip(" ,.;:")
    text = _LEADING_ARTICLES.sub("", text, count=2).strip(" ,.;:")
    return text or query.strip()


class WebEvidenceClient:
    """Bounded HTTP evidence client. Retrieved text is never executable."""

    def __init__(self, timeout: float = 8.0, max_bytes: int = 1_000_000):
        self.timeout, self.max_bytes = timeout, max_bytes
        self.headers = {"User-Agent": "ARCA-llm/0.3"}
        self._cache: dict[str, tuple[float, str]] = {}

    def _get(self, url: str) -> str:
        import time as _time

        cached = self._cache.get(url)
        if cached and _time.time() - cached[0] < 600:
            return cached[1]
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("only absolute http(s) URLs are allowed")
        with urlopen(Request(url, headers=self.headers), timeout=self.timeout) as response:
            content_type = response.headers.get("content-type", "")
            if content_type and not any(x in content_type for x in ("text/", "json", "xml")):
                raise ValueError(f"unsupported content type: {content_type}")
            text = response.read(self.max_bytes).decode("utf-8", errors="replace")
        if len(self._cache) > 64:
            self._cache.clear()
        self._cache[url] = (_time.time(), text)
        return text

    def fetch(self, url: str) -> WebResult:
        raw = self._get(url)
        parser = _TextParser(); parser.feed(raw)
        text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
        return WebResult(urlparse(url).netloc, url, text[:400], text, urlparse(url).netloc)

    def search(self, query: str, limit: int = 5) -> list[WebResult]:
        """Merged evidence, best first: the encyclopedic lead definition
        (REST summary), then title/full-text search, then DuckDuckGo for
        practical diversity. Brand-name collisions ('Barco' company vs 'barco'
        ship) therefore lose against the actual concept entry."""
        merged: list[WebResult] = []
        seen: set[str] = set()
        sources = (
            self._search_wikipedia_summary,
            self._search_wikipedia,
            self._search_wikipedia_fulltext,
            self._search_ddg,
        )
        for source in sources:
            try:
                batch = source(query, limit)
            except Exception:
                # One engine being down or rate-limited must never kill the rest.
                batch = []
            for result in batch:
                key = result.url.casefold()
                if key in seen:
                    continue
                seen.add(key)
                merged.append(result)
        return merged[:limit]

    def _search_wikipedia_summary(self, query: str, limit: int = 5) -> list[WebResult]:
        """Clean lead-definition paragraph: REST summary first, TextExtracts as
        resilient fallback (both return the article intro without HTML quirks)."""
        keywords = keywords_from(query).strip()
        if not keywords:
            return []
        candidates = [keywords]
        words = keywords.split()
        if len(words) > 1:
            candidates.append(words[0])
        else:
            candidates = list(candidates)
        for candidate in candidates:
            extract, title, url = self._summary_rest(candidate)
            if len(extract) <= 80:
                extract, title, url = self._summary_textextracts(candidate)
            if len(extract) > 80:
                trimmed = extract.strip()
                if trimmed[-1] not in ".!?…:":
                    trimmed += "."
                return [WebResult(
                    title=title or candidate,
                    url=url,
                    snippet="",
                    text=trimmed,
                    source="wikipedia-summary",
                )]
        # Accent-less/typo queries: resolve a real title through opensearch,
        # then take that article's clean intro.
        resolved = self._search_wikipedia(keywords, 1)
        if resolved:
            extract, title, url = self._summary_textextracts(resolved[0].title)
            if len(extract) > 80:
                return [WebResult(title=title or resolved[0].title, url=url, snippet="", text=extract, source="wikipedia-summary")]
        return []

    def _summary_rest(self, title: str) -> tuple[str, str, str]:
        try:
            api = "https://es.wikipedia.org/api/rest_v1/page/summary/" + quote(title.replace(" ", "_"))
            data = json.loads(self._get(api))
            if data.get("type") != "standard":
                return "", "", ""
            url = str((data.get("content_urls") or {}).get("desktop", {}).get("page", ""))
            return str(data.get("extract") or ""), str(data.get("title") or ""), url
        except (ValueError, OSError, KeyError, TypeError):
            return "", "", ""

    def _summary_textextracts(self, title: str) -> tuple[str, str, str]:
        try:
            api = (
                "https://es.wikipedia.org/w/api.php?action=query&format=json"
                "&prop=extracts&exintro=1&explaintext=1&redirects=1&titles="
                + quote(title.replace(" ", "_"))
            )
            data = json.loads(self._get(api))
            pages = (data.get("query") or {}).get("pages") or {}
            page = next(iter(pages.values()), {})
            extract = str(page.get("extract") or "").strip()
            normalized_title = str(page.get("title") or title)
            return extract, normalized_title, self._article_url(normalized_title)
        except (ValueError, OSError, KeyError, StopIteration, TypeError):
            return "", "", ""

    @staticmethod
    def _article_url(title: str) -> str:
        return "https://es.wikipedia.org/wiki/" + quote_plus(title.strip().replace(" ", "_"))

    def _search_wikipedia(self, query: str, limit: int = 5) -> list[WebResult]:
        """Title-search fallback when DuckDuckGo is unavailable or rate-limited."""
        if not query.strip():
            return []
        try:
            api = f"https://es.wikipedia.org/w/api.php?action=opensearch&format=json&limit={limit}&search=" + quote_plus(keywords_from(query))
            data = json.loads(self._get(api))
            return [WebResult(title=title, url=url, snippet=snippet or title, source="wikipedia") for title, snippet, url in zip(data[1], data[2], data[3]) if url]
        except (ValueError, OSError, KeyError, IndexError, TypeError):
            return []

    def _search_wikipedia_fulltext(self, query: str, limit: int = 5) -> list[WebResult]:
        """Full-text search with automatic spelling-suggestion retry."""
        term = keywords_from(query)
        tried: set[str] = set()
        for _ in range(2):
            if not term or term in tried:
                break
            tried.add(term)
            try:
                api = (
                    "https://es.wikipedia.org/w/api.php?action=query&list=search"
                    f"&srlimit={limit}&srinfo=suggestion&srprop=snippet&format=json&srsearch="
                    + quote_plus(term)
                )
                data = json.loads(self._get(api))
                query_block = data.get("query", {})
                hits = query_block.get("search", [])
                if hits:
                    return [
                        WebResult(
                            title=hit["title"],
                            url=self._article_url(hit["title"]),
                            snippet=re.sub(r"<[^>]+>", "", hit.get("snippet", "")) or hit["title"],
                            source="wikipedia",
                        )
                        for hit in hits
                        if hit.get("title")
                    ]
                term = str(query_block.get("searchinfo", {}).get("suggestion") or "")
            except (ValueError, OSError, KeyError, IndexError, TypeError):
                break
        words = sorted(keywords_from(query).split(), key=len, reverse=True)
        if words and len(words) > 1:
            return self._search_wikipedia(words[0], limit)
        return []

    def _search_ddg(self, query: str, limit: int = 5) -> list[WebResult]:
        if not query.strip():
            return []
        raw = self._get("https://lite.duckduckgo.com/lite/?q=" + quote_plus(keywords_from(query)))
        # DuckDuckGo Lite wraps result links in /l/?uddg=<url-encoded-target>
        # redirects. Keep this intentionally conservative: failed parsing means
        # no evidence, not guesses. A rate-limited response yields only
        # self-referential links, which are filtered below and trigger the
        # Wikipedia fallback.
        links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', raw, re.I | re.S)
        results: list[WebResult] = []
        for href, title_html in links:
            title = re.sub(r"<[^>]+>", " ", html.unescape(title_html)).strip()
            if not title:
                continue
            absolute = urljoin("https://lite.duckduckgo.com", href)
            target = self._unwrap_redirect(absolute)
            netloc = urlparse(target).netloc.casefold()
            if not target or netloc == "" or netloc.endswith("duckduckgo.com"):
                continue
            results.append(WebResult(title, target, title, source="duckduckgo"))
            if len(results) >= limit:
                break
        return results

    @staticmethod
    def _unwrap_redirect(url: str) -> str:
        if "/l/?" not in url and "uddg=" not in url:
            return url
        try:
            query_string = urlparse(url).query
            params = parse_qs(query_string)
            candidates = params.get("uddg") or []
            return unquote(candidates[0]) if candidates else url
        except ValueError:
            return ""
