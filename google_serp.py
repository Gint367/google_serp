import asyncio
import json
import os.path
from pprint import pprint
from typing import Any, Dict, List
from urllib.parse import quote
from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    BrowserConfig,
    JsonCssExtractionStrategy,
    LLMConfig,
    CrawlResult,
    CacheMode,
)


async def search(q: str = "apple inc") -> Dict[str, Any]:
    print("Searching for:", q)
    browser_config = BrowserConfig(headless=True, verbose=True)
    crawler = AsyncWebCrawler(config=browser_config)
    search_result: Dict[str, List[Dict[str, Any]]] = {}
    await crawler.start()
    try:
        crawl_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            keep_attrs=["id", "class"],
            keep_data_attributes=True,
            delay_before_return_html=2.0,
            # css_selector="div#search"
        )

        result: CrawlResult = await crawler.arun(
            f"https://www.google.com/search?q={quote(q)}",
            config=crawl_config,
        )

        if result.success:
            schemas: Dict[str, Any] = await build_schema(result.html)
            # print("Schemas:", schemas)
            for schema in schemas.values():
                schema_key = schema["name"].lower().replace(" ", "_")
                # print(f"Schema key: {schema_key}")
                search_result[schema_key] = JsonCssExtractionStrategy(
                    schema=schema,
                ).run(url="", sections=[result.html])
                # pprint(search_result[schema_key])

        with open("search_result.json", "w", encoding="utf-8") as file:
            json.dump(search_result, file, indent=4, ensure_ascii=False)
    finally:
        await crawler.close()
    return search_result


async def build_schema(cleaned_html, force: bool = False) -> Dict[str, Any]:
    schemas = {}
    if os.path.exists("google_serp/schemas/organic_schema.json") and not force:
        with open(
            "google_serp/schemas/organic_schema.json", "r", encoding="utf-8"
        ) as f:
            schemas["organic"] = json.load(f)
    else:
        print("Building organic_schema...")
        # extract schema from html
        organic_schema = JsonCssExtractionStrategy.generate_schema(
            html=cleaned_html,
            llm_config=LLMConfig(
                provider="gemini/gemini-2.0-flash",
            ),
            target_json_example="""{
                "name": "...",
                "title": "...",
                "snippet": "...",
                "date": "22 Feb 2025",
                "attributes": "...",
            }""",
            query="""The given html is the crawled html from Google search result. Please find the schema for organic search item in the given html. I am interested in title, link, snippet text, sitelinks and date.
            """,
        )
        with open(
            "google_serp/schemas/organic_schema.json", "w", encoding="utf-8"
        ) as f:
            json.dump(organic_schema, f, indent=4, ensure_ascii=False)
        schemas["organic"] = organic_schema

    # Repeat for featured snippet

    if os.path.exists("google_serp/schemas/featured_snippet_schema.json") and not force:
        with open(
            "google_serp/schemas/featured_snippet_schema.json", "r", encoding="utf-8"
        ) as f:
            schemas["featured_snippet"] = json.load(f)
    else:
        # extract schema from html
        # First try to load reference HTML from the sample file
        print("Building featured_snippet_schema...")
        featured_snippet_schema = JsonCssExtractionStrategy.generate_schema(
            html=cleaned_html,
            llm_config=LLMConfig(
                provider="gemini/gemini-2.0-flash",
            ),
            target_json_example="""{
                "name": "...",
                "snippet": "...",
                "date": "22 Feb 2025",
                "sitelinks": [
                    {
                        "title": "...",
                        "link": "...",
                    }
                ],
            }""",
            query="""The given html is the a part of crawled html from Google search result. Please find the schema for featured snippet in the given html.Featured snippet is usually just one section at the topmost of the page with just one or two sitelinks. I am interested in title, link, snippet text, date, and sitelinks associated with the snippet.
            """,
        )
        with open(
            "google_serp/schemas/featured_snippet_schema.json", "w", encoding="utf-8"
        ) as f:
            json.dump(featured_snippet_schema, f, indent=4, ensure_ascii=False)
        schemas["featured_snippet"] = featured_snippet_schema
    return schemas


if __name__ == "__main__":
    asyncio.run(search("bde-engineering ceo"))
