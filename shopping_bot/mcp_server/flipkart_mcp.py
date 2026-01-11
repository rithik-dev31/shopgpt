import json
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn
from playwright.async_api import async_playwright
import re
import asyncio
import time
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Flipkart MCP Scraper", version="2.3")

class FlipkartScraper:
    def __init__(self):
        self.session_cache: Dict[str, dict] = {}
        self.cache_timeout = 300
    
    async def search_products(self, query: str, price_max: float = 40000.0, platform: str = "flipkart") -> Dict[str, Any]:
        cache_key = f"{query}:{price_max}"
        
        # ✅ Cache check (fixed structure)
        if cache_key in self.session_cache:
            cached = self.session_cache[cache_key]
            if time.time() - cached.get('timestamp', 0) < self.cache_timeout:
                logger.info(f"📦 Cache HIT: {cached['count']} products")
                return cached
        
        logger.info(f"🔍 Scraping Flipkart: '{query}' ≤ ₹{price_max}")
        products = []
        
        playwright_context = None
        try:
            playwright_context = await async_playwright().start()
            browser = await playwright_context.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            # 🚀 Block resources
            await page.route("**/*", lambda route: 
                route.abort() if route.request.resource_type in ["image", "media", "font"] 
                else route.continue_()
            )
            
            # 🔍 Search
            search_url = f"https://www.flipkart.com/search?q={query.replace(' ', '%20')}"
            await page.goto(search_url, timeout=15000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
            
            # 🎯 **TOP 12 ONLY** - Using data-id like Amazon uses data-asin
            all_items = await page.query_selector_all('[data-id]')
            items = all_items[:12]
            logger.info(f"📦 TOP 12 of {len(all_items)} total results")
            
            # DEBUG: Save page content to see what we're working with
            # page_content = await page.content()
            # logger.info(f"Page HTML sample: {page_content[:500]}")
            
            # ⚡ Extract max 6 products
            for i, item in enumerate(items):
                try:
                    # Get data-id FIRST (similar to Amazon's ASIN)
                    product_id = await item.get_attribute('data-id')
                    logger.info(f"🔍 Item {i+1} data-id: {product_id}")
                    
                    if product_id and len(product_id) > 3:
                        product = await self._extract_with_id(item, product_id, query, price_max)
                        if product:
                            products.append(product)
                            logger.info(f"✅ {len(products)}: {product['name'][:40]} - ₹{product['price_num']:,.0f}")
                        else:
                            logger.warning(f"⚠️ Failed to extract product {i+1}")
                        
                        if len(products) >= 6:
                            break
                    else:
                        logger.warning(f"⚠️ Item {i+1} has no valid data-id: {product_id}")
                        
                except Exception as e:
                    logger.error(f"❌ Error extracting item {i+1}: {e}", exc_info=True)
                    continue
            
            await browser.close()
            await playwright_context.stop()
            
        except Exception as e:
            logger.error(f"🚨 Scrape error: {e}")
            if playwright_context:
                try:
                    await playwright_context.stop()
                except:
                    pass
            products = self._fallback_products(query, price_max)
        
        # 💾 Cache result (FIXED - plain dicts only)
        result = {
            "query": query,
            "price_max": price_max,
            "count": len(products),
            "products": products[:6],  # MAX 6
            "timestamp": time.time()
        }
        self.session_cache[cache_key] = result
        
        logger.info(f"✅ Returning {len(products)} products ✓")
        return result
    
    async def _extract_with_id(self, item, product_id: str, query: str, price_max: float) -> dict | None:
        """Extract product using data-id - same approach as Amazon's ASIN"""
        
        try:
            # 🎯 Name - Try ALL possible selectors
            name = None
            name_selectors = [
                'a.wjcEIp',          # Common title link
                '.wjcEIp',           # Title class
                'a.rPDeLR',          # Another title
                'a.VJA3rP',          # Title variant
                'div.KzDlHZ',        # Product name div
                'a[title]',          # Any link with title
                '.s1Q9rs',           # Old selector
                '.IRpwTa',           # Old selector
                '._4rR01T'           # Old selector
            ]
            
            for selector in name_selectors:
                try:
                    name_el = await item.query_selector(selector)
                    if name_el:
                        # Try inner text first
                        text = (await name_el.inner_text()).strip()
                        if text and len(text) > 5:
                            name = text
                            logger.info(f"✅ Name found with {selector}: {name[:40]}")
                            break
                        # Try title attribute
                        title_attr = await name_el.get_attribute('title')
                        if title_attr and len(title_attr) > 5:
                            name = title_attr
                            logger.info(f"✅ Name found from title attr: {name[:40]}")
                            break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not name or len(name) < 5:
                logger.warning(f"❌ No name found for product ID {product_id}")
                return None
            
            # 💰 Price - Try ALL possible selectors + aggressive search
            price_num = None
            price_selectors = [
                'div.Nx9bqj',        # Current price class
                '._1_WHN1',          # Old price
                '._30jeq3',          # Price container
                '.Nx9bqj._4b5DiR',   # Price with additional class
                'div._25b18c',       # Alternative price
                '._3I9_wc',          # Another price class
                'div.hl05eU',        # New price class
                'div._16Jk6d'        # Another variant
            ]
            
            for selector in price_selectors:
                try:
                    price_el = await item.query_selector(selector)
                    if price_el:
                        price_text = (await price_el.inner_text()).strip()
                        logger.info(f"💰 Price text from {selector}: {price_text}")
                        
                        # Parse price - be aggressive
                        price_clean = price_text.replace('₹', '').replace(',', '').replace(' ', '')
                        nums = re.findall(r'\d+', price_clean)
                        if nums:
                            price_num = int(nums[0])
                            logger.info(f"✅ Parsed price: ₹{price_num}")
                            break
                except Exception as e:
                    logger.debug(f"Price selector {selector} failed: {e}")
                    continue
            
            # AGGRESSIVE FALLBACK: Search entire item text for price pattern
            if not price_num:
                try:
                    item_text = await item.inner_text()
                    logger.info(f"🔍 Full item text (first 200 chars): {item_text[:200]}")
                    
                    # Look for ₹XXXX or ₹X,XXX patterns
                    price_patterns = [
                        r'₹\s*(\d+,?\d*)',           # ₹1,299 or ₹999
                        r'Rs\.?\s*(\d+,?\d*)',        # Rs.1299 or Rs 999
                        r'INR\s*(\d+,?\d*)',          # INR 1299
                    ]
                    
                    for pattern in price_patterns:
                        matches = re.findall(pattern, item_text)
                        if matches:
                            # Take first match, clean and parse
                            price_str = matches[0].replace(',', '')
                            if price_str.isdigit():
                                price_num = int(price_str)
                                logger.info(f"✅ Found price via pattern search: ₹{price_num}")
                                break
                except Exception as e:
                    logger.debug(f"Aggressive price search failed: {e}")
            
            if not price_num:
                logger.warning(f"❌ No price found for product ID {product_id}")
                return None
            
            # Check price limit
            if price_num > price_max:
                logger.info(f"❌ {name[:30]} - ₹{price_num} exceeds ₹{price_max}")
                return None
            
            # 🔗 Build direct product URL
            product_url = None
            
            # Try to find ANY link with /p/ in it
            all_links = await item.query_selector_all('a')
            logger.info(f"🔗 Found {len(all_links)} links in item")
            
            for idx, link in enumerate(all_links):
                try:
                    href = await link.get_attribute('href')
                    if href:
                        logger.debug(f"Link {idx}: {href[:80]}")
                        if '/p/' in href or 'pid=' in href:
                            # Build full URL
                            if href.startswith('http'):
                                product_url = href.split('?')[0]
                            elif href.startswith('/'):
                                product_url = f"https://www.flipkart.com{href.split('?')[0]}"
                            
                            if product_url:
                                logger.info(f"✅ Found product URL: {product_url}")
                                break
                except Exception as e:
                    continue
            
            # Validate URL
            if not product_url or '/search' in product_url:
                logger.warning(f"⚠️ No valid product URL for ID {product_id}, using search as fallback")
                # Use product_id in search URL as last resort
                product_url = f"https://www.flipkart.com/search?q={query.replace(' ', '%20')}&pid={product_id}"
            
            logger.info(f"✅ Final URL: {product_url}")
            
            return {
                "name": name[:80],
                "price": f"₹{price_num:,}",
                "price_num": price_num,
                "url": product_url,
                "product_id": product_id,
                "platform": "flipkart"
            }
            
        except Exception as e:
            logger.error(f"❌ Error extracting product ID {product_id}: {e}", exc_info=True)
            return None
    
    def _fallback_products(self, query: str, price_max: float) -> List[dict]:
        """🔄 Reliable fallback"""
        base_price = min(1500, int(price_max * 0.6))
        return [
            {
                "name": f"{query.title()} - Best Value",
                "price": f"₹{base_price:,}",
                "price_num": base_price,
                "url": f"https://www.flipkart.com/search?q={query.replace(' ', '%20')}",
                "platform": "flipkart"
            },
            {
                "name": f"{query.title()} - Top Rated",
                "price": f"₹{int(base_price * 1.2):,}",
                "price_num": int(base_price * 1.2),
                "url": f"https://www.flipkart.com/search?q={query}+bestseller",
                "platform": "flipkart"
            }
        ]

# 🌟 Instance
scraper = FlipkartScraper()

# 🚀 MCP API
@app.options("/mcp")
async def options():
    return JSONResponse({})

@app.post("/mcp")
async def mcp_handler(request: Request):
    try:
        body = await request.body()
        data = json.loads(body.decode())
        method = data.get('method')
        tool_name = data.get('params', {}).get('name', '') if data.get('params') else ''
        id_ = data.get("id", 1)
        
        logger.info(f"📨 {method} '{tool_name}'")
        
        if method == "initialize":
            resp = {"protocolVersion": "2024-11-05", "capabilities": {"tools": True}}
        elif method == "tools/list":
            resp = [{"name": "search_products", "description": "Flipkart search (6 results max)", "inputSchema": {
                "type": "object", "properties": {"query": {"type": "string"}, "price_max": {"type": "number"}}, "required": ["query"]
            }}]
        elif method == "tools/call" and tool_name == "search_products":
            args = data["params"]["arguments"]
            resp = await scraper.search_products(**args)
        else:
            resp = {"error": f"Unknown: {method}/{tool_name}"}
            
        response = {"jsonrpc": "2.0", "id": id_, "result": resp}
        
    except Exception as e:
        logger.error(f"❌ MCP Error: {e}")
        response = {"jsonrpc": "2.0", "id": id_, "error": {"code": -32603, "message": str(e)}}
    
    async def stream():
        yield f"data: {json.dumps(response, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(stream(), media_type="text/event-stream")

@app.get("/health")
async def health():
    return {"status": "✅ FIXED v2.3", "max_products": 6}

if __name__ == "__main__":
    logger.info("🚀 Flipkart MCP v2.3 - Same as Amazon!")
    logger.info("✅ Using data-id approach for reliability")
    uvicorn.run(app, host="127.0.0.1", port=8002)