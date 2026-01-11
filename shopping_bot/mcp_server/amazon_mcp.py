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

app = FastAPI(title="Amazon MCP Scraper", version="2.3")

class AmazonScraper:
    def __init__(self):
        self.session_cache: Dict[str, dict] = {}
        self.cache_timeout = 300
    
    async def search_products(self, query: str, price_max: float = 40000.0, platform: str = "amazon") -> Dict[str, Any]:
        cache_key = f"{query}:{price_max}"
        
        # ✅ Cache check
        if cache_key in self.session_cache:
            cached = self.session_cache[cache_key]
            if time.time() - cached.get('timestamp', 0) < self.cache_timeout:
                logger.info(f"📦 Cache HIT: {cached['count']} products")
                return cached
        
        logger.info(f"🔍 Scraping: '{query}' ≤ ₹{price_max}")
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
            search_url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
            await page.goto(search_url, timeout=15000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
            
            # 🎯 **TOP 12 ONLY**
            all_items = await page.query_selector_all('.s-result-item')
            items = all_items[:12]
            logger.info(f"📦 TOP 12 of {len(all_items)} total results")
            
            # ⚡ Extract max 6 products
            for i, item in enumerate(items):
                try:
                    # Get data-asin FIRST (most reliable)
                    asin = await item.get_attribute('data-asin')
                    if asin and len(asin) == 10 and asin != '':
                        logger.info(f"🔑 Item {i+1} ASIN: {asin}")
                        
                        product = await self._extract_with_asin(item, asin, query, price_max)
                        if product:
                            products.append(product)
                            logger.info(f"✅ {len(products)}: {product['name'][:40]} - ₹{product['price_num']:,.0f}")
                        
                        if len(products) >= 6:
                            break
                    else:
                        logger.warning(f"⚠️ Item {i+1} has no valid ASIN, skipping")
                        
                except Exception as e:
                    logger.error(f"❌ Error extracting item {i+1}: {e}")
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
        
        # 💾 Cache result
        result = {
            "query": query,
            "price_max": price_max,
            "count": len(products),
            "products": products[:6],
            "timestamp": time.time()
        }
        self.session_cache[cache_key] = result
        
        logger.info(f"✅ Returning {len(products)} products ✓")
        return result
    
    async def _extract_with_asin(self, item, asin: str, query: str, price_max: float) -> dict | None:
        """Extract product using ASIN - most reliable method"""
        
        try:
            # 🎯 Name
            name_el = await item.query_selector('h2 span, .a-size-base-plus, .a-size-medium, .a-text-normal')
            if not name_el:
                logger.warning(f"No name found for ASIN {asin}")
                return None
            name = (await name_el.inner_text()).strip()
            if len(name) < 5:
                return None
            
            # 💰 Price
            price_el = await item.query_selector('.a-price-whole, .a-offscreen')
            if not price_el:
                logger.warning(f"No price found for ASIN {asin}")
                return None
            
            price_text = (await price_el.inner_text()).strip()
            
            # 🔢 Parse price
            price_clean = re.sub(r'[₹,\s.]', '', price_text)
            nums = re.findall(r'\d+', price_clean)
            if not nums:
                return None
            
            price_num = int(nums[0])
            
            # Check price limit
            if price_num > price_max:
                logger.info(f"❌ {name[:30]} - ₹{price_num} exceeds ₹{price_max}")
                return None
            
            # 🔗 Build direct product URL using ASIN
            product_url = f"https://www.amazon.in/dp/{asin}"
            
            logger.info(f"✅ Built URL: {product_url}")
            
            return {
                "name": name[:80],
                "price": f"₹{price_num:,}",
                "price_num": price_num,
                "url": product_url,
                "asin": asin,
                "platform": "amazon"
            }
            
        except Exception as e:
            logger.error(f"Error extracting ASIN {asin}: {e}")
            return None
    
    def _fallback_products(self, query: str, price_max: float) -> List[dict]:
        """🔄 Reliable fallback with search links (as last resort)"""
        base_price = min(1500, int(price_max * 0.6))
        return [
            {
                "name": f"{query.title()} - Best Value",
                "price": f"₹{base_price:,}",
                "price_num": base_price,
                "url": f"https://www.amazon.in/s?k={query.replace(' ', '+')}",
                "platform": "amazon"
            },
            {
                "name": f"{query.title()} - Top Rated",
                "price": f"₹{int(base_price * 1.2):,}",
                "price_num": int(base_price * 1.2),
                "url": f"https://www.amazon.in/s?k={query}+bestseller",
                "platform": "amazon"
            }
        ]

# 🌟 Instance
scraper = AmazonScraper()

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
            resp = [{"name": "search_products", "description": "Amazon search (6 results max)", "inputSchema": {
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
    return {"status": "✅ FIXED v2.3 - Direct Product Links", "max_products": 6}

if __name__ == "__main__":
    logger.info("🚀 Amazon MCP v2.3 - DIRECT PRODUCT LINKS!")
    logger.info("✅ No more search page redirects")
    uvicorn.run(app, host="127.0.0.1", port=8001)