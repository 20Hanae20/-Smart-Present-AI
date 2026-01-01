#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

TARGETS = [
    "https://sites.google.com/view/ista-ntic-sm/",
    "https://sites.google.com/view/ista-ntic-sm/emplois-du-temps",
    "https://sites.google.com/view/ista-ntic-sm/documents",
    "https://sites.google.com/view/ista-ntic-sm/résultats-fin-année",
]

async def grab(page, url):
    await page.goto(url, wait_until="networkidle")
    # Extract visible text from body
    text = await page.evaluate("document.body.innerText")
    print("URL:", url)
    print("CHARS:", len(text))
    print(text[:1200])
    print("\n" + "="*80 + "\n")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        for u in TARGETS:
            await grab(page, u)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
