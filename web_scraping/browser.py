import asyncio
import base64
import json
from pathlib import Path

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright

PATH = "/Users/USER/Desktop/army/training_DE/Hafifa/web_scraping"

output_dir = Path(f"{PATH}/output")
output_dir.mkdir(parents=True, exist_ok=True)

with open(f"{PATH}/urls.input") as f:
    urls = f.read().split()


async def get_html(page):
    """
    HTML Content: Extract all the HTML content of the page (as a string).
    This should be saved in the json file under the key "html".
    """
    return await page.content()


def get_resources(page):
    """
    Page Resources: List all URLs that were loaded during the page load (such as images, external links, etc.).
    This list should be saved in the json file under the key "resources".
    """
    resources = []
    page.on("request", lambda request: resources.append(request.url))
    return resources


async def save_screenshot(page, path):
    """
    Page Screenshot: Take a screenshot of the first page and save it in the directory as screenshot.png.
    """
    await page.screenshot(path=path)


def encode_image_base64(path):
    """
    Base64 Encoded Image: Convert the saved screenshot to a base64 encoded string.
    This should be saved in the json file under the key "screenshot".
    """
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome")
        for i, url in enumerate(urls, start=1):
            url_dir = output_dir / f"url_{i}"
            url_dir.mkdir(parents=True, exist_ok=True)

            page = await browser.new_page()
            try:
                resources = get_resources(page)
                await page.goto(url, wait_until="load", timeout=100000)
                html = await get_html(page)
                screenshot_path = url_dir / "screenshot.png"
                await save_screenshot(page, screenshot_path)
                page_data = {
                    "html": html,
                    "resources": resources,
                    "screenshot": encode_image_base64(screenshot_path),
                }

                await asyncio.to_thread(save_json, url_dir / "browse.json", page_data)

            except PlaywrightError as error:  # covers timeouts too
                print(f"Failed to scrape {url}: {error.message.splitlines()[0]}")
            finally:
                await page.close()
        await browser.close()


asyncio.run(main())
