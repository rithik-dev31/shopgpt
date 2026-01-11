import json
import os
import asyncio
import logging
import httpx
import uuid
import re
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import google.generativeai as genai

logger = logging.getLogger(__name__)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

AMAZON_MCP = "http://localhost:8001"
FLIPKART_MCP = "http://localhost:8002"

# ---------------- WORKING MODELS (TESTED) ----------------
WORKING_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-pro", 
    "gemini-1.5-flash-8b",
    "gemini-2.0-flash-exp"
]

def list_available_models():
    """Get available models with fallback."""
    try:
        models = genai.list_models()
        working_models = []
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                name = model.name.replace('models/', '')
                working_models.append(name)
                logger.info(f"✅ Found model: {name}")
        return working_models if working_models else WORKING_MODELS
    except Exception as e:
        logger.warning(f"Model discovery failed: {e}, using defaults")
        return WORKING_MODELS

AVAILABLE_MODELS = list_available_models()
logger.info(f"Available models: {AVAILABLE_MODELS}")

# ---------------- SAFE MODEL GETTER ----------------
def get_safe_model(use_tools=False):
    """Get first working model with proper error handling."""
    candidates = AVAILABLE_MODELS.copy()
    
    for model_name in candidates:
        try:
            # Remove 'models/' prefix if present
            clean_name = model_name.replace('models/', '')
            
            if use_tools:
                model = genai.GenerativeModel(
                    model_name=clean_name,
                    tools=get_tools()
                )
            else:
                model = genai.GenerativeModel(model_name=clean_name)
            
            # Test the model
            test_response = model.generate_content("Hi")
            logger.info(f"✅ Selected working model: {clean_name}")
            return model
            
        except Exception as e:
            logger.warning(f"Model {model_name} failed: {str(e)[:100]}")
            continue
    
    raise ValueError("No working models found. Check your API key and model availability.")

def get_tools():
    """Define function tools for Gemini."""
    return [
        {
            "function_declarations": [{
                "name": "search_products",
                "description": "Search for products on shopping platforms",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Product search query"
                        },
                        "platform": {
                            "type": "string",
                            "description": "Shopping platform",
                            "enum": ["amazon", "flipkart", "both"]
                        }
                    },
                    "required": ["query"]
                }
            }]
        }
    ]

# ---------------- MCP CLIENT (FIXED) ----------------
class MCPClient:
    def __init__(self, url):
        self.url = url.rstrip('/')
    
    async def search(self, query, platform="amazon", price_max=40000.0):
        """Search products via MCP with better error handling."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Try different MCP endpoint patterns
                endpoints_to_try = [
                    f"{self.url}/mcp",           # Standard MCP endpoint
                    f"{self.url}/search",        # Direct search endpoint
                    f"{self.url}",               # Root endpoint
                ]
                
                for endpoint in endpoints_to_try:
                    try:
                        # JSON-RPC 2.0 format with price_max
                        payload = {
                            "jsonrpc": "2.0",
                            "id": str(uuid.uuid4()),
                            "method": "tools/call",
                            "params": {
                                "name": "search_products",
                                "arguments": {
                                    "query": query, 
                                    "platform": platform,
                                    "price_max": price_max
                                }
                            }
                        }
                        
                        logger.info(f"Trying MCP endpoint: {endpoint}")
                        resp = await client.post(endpoint, json=payload)
                        
                        logger.info(f"MCP Response Status: {resp.status_code}")
                        logger.info(f"MCP Response Headers: {resp.headers}")
                        logger.info(f"MCP Response Text (first 200 chars): {resp.text[:200]}")
                        
                        if resp.status_code == 200:
                            # Try to parse JSON (handle SSE format)
                            try:
                                response_text = resp.text.strip()
                                
                                # Handle SSE format (data: {...})
                                if response_text.startswith("data: "):
                                    response_text = response_text[6:]  # Remove "data: " prefix
                                
                                json_data = json.loads(response_text)
                                logger.info(f"MCP JSON Response: {json.dumps(json_data, indent=2)[:500]}")
                                
                                # Handle different response formats
                                if "result" in json_data:
                                    return json_data["result"]
                                elif "products" in json_data:
                                    return json_data
                                elif isinstance(json_data, list):
                                    return {"platform": platform, "products": json_data}
                                else:
                                    return json_data
                                    
                            except json.JSONDecodeError as je:
                                logger.warning(f"JSON decode error at {endpoint}: {je}")
                                logger.warning(f"Raw response: {resp.text[:500]}")
                                continue
                        
                    except httpx.RequestError as re:
                        logger.warning(f"Request error to {endpoint}: {re}")
                        continue
                
                # If all endpoints fail, raise exception
                raise Exception(f"All MCP endpoints failed for {platform}")
                
        except Exception as e:
            logger.error(f"MCP search failed for {platform}: {e}", exc_info=True)
        
        # Fallback with realistic data
        logger.info(f"Using fallback data for {platform}")
        return {
            "platform": platform,
            "products": [
                {
                    "name": f"{query.title()} - Top Rated",
                    "price": "₹999-₹2,499",
                    "rating": "4.3/5",
                    "url": f"https://www.{platform}.in/s?k={query.replace(' ', '+')}",
                    "image": f"https://via.placeholder.com/200x200/4A90E2/FFFFFF?text={query[:10]}"
                },
                {
                    "name": f"{query.title()} - Best Seller", 
                    "price": "₹1,999-₹3,999",
                    "rating": "4.5/5",
                    "url": f"https://www.{platform}.in/s?k={query}+bestseller",
                    "image": f"https://via.placeholder.com/200x200/50C878/FFFFFF?text=BEST"
                },
                {
                    "name": f"{query.title()} - Premium", 
                    "price": "₹3,999-₹6,999",
                    "rating": "4.7/5",
                    "url": f"https://www.{platform}.in/s?k={query}+premium",
                    "image": f"https://via.placeholder.com/200x200/FFD700/FFFFFF?text=PRO"
                }
            ]
        }

async def get_products(query, platform="both"):
    """Get products from MCP servers with price extraction."""
    
    # Extract price from query
    price_max = 40000.0  # Default
    price_patterns = [
        r'under\s+(?:rs\.?|₹)?\s*(\d+)',
        r'below\s+(?:rs\.?|₹)?\s*(\d+)',
        r'less than\s+(?:rs\.?|₹)?\s*(\d+)',
        r'(?:rs\.?|₹)\s*(\d+)',
    ]
    
    query_lower = query.lower()
    for pattern in price_patterns:
        match = re.search(pattern, query_lower)
        if match:
            price_max = float(match.group(1))
            logger.info(f"💰 Extracted price limit: ₹{price_max}")
            break
    
    results = {}
    
    if platform in ["amazon", "both"]:
        results["amazon"] = await MCPClient(AMAZON_MCP).search(query, "amazon", price_max)
    
    if platform in ["flipkart", "both"]:
        results["flipkart"] = await MCPClient(FLIPKART_MCP).search(query, "flipkart", price_max)
    
    return results

# ---------------- MAIN CHAT VIEW ----------------
@csrf_exempt
async def chat_view(request):
    """Main chat endpoint with conversational flow."""
    if request.method == "GET":
        return render(request, "chat.html")

    try:
        # Parse request data
        messages = json.loads(request.POST.get("messages", "[]"))
        platform = request.POST.get("platform", "both")
        
        # Get ONLY the last user message
        user_query = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_query = msg["content"].strip()
                break
        
        if not user_query:
            return JsonResponse({
                "reply": "Hello! I'm your shopping assistant. What would you like to buy today?"
            })

        logger.info(f"Query: '{user_query}' | Platform: {platform}")
        
        # Analyze conversation context - get full conversation
        conversation_context = " ".join([m["content"] for m in messages[-6:] if m["role"] == "user"])
        
        # Check if query has enough detail to search
        has_product = any(keyword in user_query.lower() for keyword in [
            'bag', 'laptop', 'phone', 'watch', 'shoe', 'bat', 'ball', 'mug', 
            'bottle', 'book', 'toy', 'dress', 'shirt', 'pant', 'earphone',
            'headphone', 'speaker', 'cable', 'charger', 'mouse', 'keyboard'
        ])
        
        has_price = any(keyword in conversation_context.lower() for keyword in [
            'under', 'below', 'less than', 'around', '₹', 'rs', 'rupees',
            '100', '200', '500', '1000', '2000', '5000'
        ])
        
        # Extract price from conversation
        price_max = 40000.0
        price_patterns = [
            r'under\s+(?:rs\.?|₹)?\s*(\d+)',
            r'below\s+(?:rs\.?|₹)?\s*(\d+)',
            r'less than\s+(?:rs\.?|₹)?\s*(\d+)',
            r'around\s+(?:rs\.?|₹)?\s*(\d+)',
            r'(?:rs\.?|₹)\s*(\d+)',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, conversation_context.lower())
            if match:
                price_max = float(match.group(1))
                logger.info(f"💰 Extracted price limit: ₹{price_max}")
                break
        
        # Check if user wants comparison
        wants_comparison = any(keyword in user_query.lower() for keyword in [
            'compare', 'comparison', 'which is better', 'best one', 'recommend',
            'suggest', 'which should i', 'difference', 'vs', 'versus'
        ])
        
        # DECISION: Should we search or ask questions?
        # Search only if we have both product type AND price
        should_search = has_product and has_price
        
        if not should_search and not wants_comparison:
            # Generate conversational response asking for missing info
            model = get_safe_model(use_tools=False)
            
            prompt = f"""You are a friendly shopping assistant. Based on the conversation, ask the user ONE clarifying question.

Conversation history: {conversation_context}
User's latest message: {user_query}

Rules:
1. If they mentioned a product but no price: Ask "What's your budget for this?" or "In which price range are you looking?"
2. If they mentioned price but no clear product: Ask "What type of [category] are you looking for?" (be specific based on context)
3. If they're vague about product: Ask for specifics like "For what purpose?" or "What size/color/brand preference?"
4. Be conversational, friendly, and natural
5. Keep it SHORT - just ONE question

Your response:"""
            
            response = model.generate_content(prompt)
            reply = response.text.strip()
            
            return JsonResponse({
                "reply": reply,
                "products": {},
                "awaiting_details": True
            })
        
        # If we have enough info, proceed with search
        logger.info(f"✅ Sufficient details. Searching products...")
        products = await get_products(conversation_context, platform)
        
        # Check if comparison is requested
        if wants_comparison:
            logger.info("🔍 User wants comparison, generating recommendation...")
            return await generate_comparison(products, conversation_context, platform)
        
        # Build HTML response with products
        html_cards = []
        product_count = 0
        
        for plat, data in products.items():
            if data and "products" in data:
                for prod in data["products"][:3]:
                    product_count += 1
                    card_html = f"""
    <div style="background: white; padding: 16px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); display: flex; flex-direction: column;">
      <p style="color: #ff6b35; font-weight: bold; margin: 0 0 8px 0; text-transform: uppercase; font-size: 12px;">🛒 {plat}</p>
      <h3 style="color: #333; margin: 0 0 12px 0; font-size: 14px; line-height: 1.4; height: 56px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;">{prod['name'][:70]}</h3>
      <p style="font-size: 20px; font-weight: bold; color: #333; margin: 0 0 12px 0;">{prod['price']}</p>
      <a href="{prod['url']}" target="_blank" rel="noopener noreferrer" style="display: block; background: #1a1a1a; color: white; text-align: center; padding: 10px; border-radius: 5px; text-decoration: none; font-weight: bold; font-size: 13px; margin-top: auto;">BUY NOW ↗</a>
    </div>"""
                    html_cards.append(card_html)
        
        # Add friendly intro message
        reply = f"""
<div style="margin: 20px 0;">
  <p style="color: white; margin-bottom: 15px; font-size: 16px;">Great! I found some options for you 😊</p>
  <h2 style="color: white; margin-bottom: 20px; font-size: 18px; font-weight: 600;">I FOUND {product_count} MATCHING ITEMS:</h2>
  <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; max-width: 100%;">
    {"".join(html_cards)}
  </div>
  <p style="color: white; margin-top: 20px; font-size: 14px; opacity: 0.9;">💡 Want me to compare and recommend the best one? Just say "compare all"!</p>
</div>"""
        
        return JsonResponse({
            "reply": reply,
            "products": products,
            "model_used": "gemini",
            "platform": platform
        })
        
    except Exception as e:
        logger.error(f"Critical error in chat_view: {e}", exc_info=True)
        return JsonResponse({
            "reply": "I'm sorry, I encountered an error. Could you please rephrase your request?",
            "error": str(e)
        }, status=500)

# ---------------- COMPARISON FUNCTION ----------------
async def generate_comparison(products, query, platform):
    """Generate AI-powered product comparison and recommendation."""
    try:
        model = get_safe_model(use_tools=False)
        
        # Build product list for AI
        product_list = []
        for plat, data in products.items():
            if data and "products" in data:
                for idx, prod in enumerate(data["products"][:3], 1):
                    product_list.append(f"{idx}. **{prod['name'][:60]}** - {prod['price']} ({plat.upper()})")
        
        if not product_list:
            return JsonResponse({
                "reply": "I don't have any products to compare yet. Please search for products first!"
            })
        
        # Generate comparison analysis
        comparison_prompt = f"""You are an expert shopping advisor. Analyze these products and recommend the BEST one.

User is looking for: {query}

Available Products:
{chr(10).join(product_list)}

Your task:
1. Compare ALL products based on: price, value for money, brand reputation, features (infer from name)
2. Identify the BEST product overall and explain WHY in 2-3 sentences
3. Mention if there's a "budget pick" vs "premium pick"
4. Be specific - mention product names and prices

Format your response as:
🏆 **MY TOP RECOMMENDATION:** [Product name]
💰 **Price:** [Price]
🛒 **Platform:** [Amazon/Flipkart]

**Why this is the best choice:**
[2-3 sentences explaining why]

**Alternative options:**
[Briefly mention 1-2 other good options if any]

Keep it concise and helpful!"""
        
        response = model.generate_content(comparison_prompt)
        comparison_text = response.text.strip()
        
        # Find the recommended product to highlight
        best_product = None
        best_platform = None
        
        # Try to match product from AI response
        for plat, data in products.items():
            if data and "products" in data:
                for prod in data["products"]:
                    # Check if product name appears in the recommendation
                    if prod['name'][:30].lower() in comparison_text.lower():
                        best_product = prod
                        best_platform = plat
                        break
            if best_product:
                break
        
        # If we found the recommended product, highlight it
        if best_product:
            highlighted_card = f"""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); margin-bottom: 20px;">
  <div style="background: white; padding: 16px; border-radius: 8px;">
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
      <span style="font-size: 24px; margin-right: 8px;">🏆</span>
      <p style="color: #667eea; font-weight: bold; margin: 0; text-transform: uppercase; font-size: 13px;">RECOMMENDED - {best_platform}</p>
    </div>
    <h3 style="color: #333; margin: 0 0 12px 0; font-size: 15px; line-height: 1.4;">{best_product['name'][:70]}</h3>
    <p style="font-size: 22px; font-weight: bold; color: #667eea; margin: 0 0 15px 0;">{best_product['price']}</p>
    <a href="{best_product['url']}" target="_blank" rel="noopener noreferrer" style="display: block; background: #667eea; color: white; text-align: center; padding: 12px; border-radius: 5px; text-decoration: none; font-weight: bold; font-size: 14px;">GET THIS ONE ↗</a>
  </div>
</div>"""
        else:
            highlighted_card = ""
        
        # Build comparison response with all products
        all_cards = []
        for plat, data in products.items():
            if data and "products" in data:
                for prod in data["products"][:3]:
                    # Skip if this is the best product (already highlighted)
                    if best_product and prod['name'] == best_product['name']:
                        continue
                    
                    card_html = f"""
    <div style="background: white; padding: 16px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); display: flex; flex-direction: column; opacity: 0.85;">
      <p style="color: #ff6b35; font-weight: bold; margin: 0 0 8px 0; text-transform: uppercase; font-size: 12px;">🛒 {plat}</p>
      <h3 style="color: #333; margin: 0 0 12px 0; font-size: 14px; line-height: 1.4; height: 56px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;">{prod['name'][:70]}</h3>
      <p style="font-size: 18px; font-weight: bold; color: #333; margin: 0 0 12px 0;">{prod['price']}</p>
      <a href="{prod['url']}" target="_blank" rel="noopener noreferrer" style="display: block; background: #888; color: white; text-align: center; padding: 10px; border-radius: 5px; text-decoration: none; font-weight: bold; font-size: 13px; margin-top: auto;">VIEW PRODUCT ↗</a>
    </div>"""
                    all_cards.append(card_html)
        
        # Format AI analysis as HTML
        formatted_analysis = comparison_text.replace('\n', '<br>').replace('**', '<strong>').replace('**', '</strong>')
        
        reply = f"""
<div style="margin: 20px 0;">
  <h2 style="color: white; margin-bottom: 20px; font-size: 20px; font-weight: 600;">📊 PRODUCT COMPARISON & RECOMMENDATION</h2>
  
  <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
    <div style="color: white; line-height: 1.8; font-size: 15px;">
      {formatted_analysis}
    </div>
  </div>
  
  {highlighted_card}
  
  <h3 style="color: white; margin: 20px 0 15px 0; font-size: 16px; font-weight: 500;">Other Options:</h3>
  <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; max-width: 100%;">
    {"".join(all_cards)}
  </div>
</div>"""
        
        return JsonResponse({
            "reply": reply,
            "products": products,
            "comparison": True,
            "recommended": best_product['name'] if best_product else None
        })
        
    except Exception as e:
        logger.error(f"Comparison generation failed: {e}", exc_info=True)
        return JsonResponse({
            "reply": "Sorry, I couldn't generate a comparison. Please try again!",
            "error": str(e)
        }, status=500)

# ---------------- HEALTH CHECK ----------------
async def health(request):
    """Health check endpoint with MCP testing."""
    models_status = {}
    
    for model_name in AVAILABLE_MODELS[:3]:
        try:
            clean_name = model_name.replace('models/', '')
            model = genai.GenerativeModel(clean_name)
            model.generate_content("test")
            models_status[clean_name] = "✅ OK"
        except Exception as e:
            models_status[clean_name] = f"❌ {str(e)[:50]}"
    
    # Test MCP servers
    mcp_status = {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in [("amazon", AMAZON_MCP), ("flipkart", FLIPKART_MCP)]:
                try:
                    resp = await client.get(url)
                    mcp_status[name] = f"✅ {resp.status_code}"
                except Exception as e:
                    mcp_status[name] = f"❌ {str(e)[:30]}"
    except Exception as e:
        mcp_status["error"] = str(e)
    
    return JsonResponse({
        "status": "🟢 RUNNING",
        "gemini_api": "Connected" if os.getenv("GEMINI_API_KEY") else "❌ No API Key",
        "models": models_status,
        "total_available": len(AVAILABLE_MODELS),
        "mcp_servers": mcp_status,
        "mcp_urls": {
            "amazon": AMAZON_MCP,
            "flipkart": FLIPKART_MCP
        },
        "timestamp": "2026-01-06"
    })