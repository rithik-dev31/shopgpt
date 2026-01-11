import httpx
import json
import uuid
import asyncio

async def test_full_session():
    # Step 1: Get session via OPTIONS
    async with httpx.AsyncClient() as client:
        options_resp = await client.options("http://localhost:8001/mcp")
        print(f"OPTIONS: {options_resp.status_code}")
        session_id = options_resp.headers.get('mcp-session-id')
        print(f"Session: {session_id}")
        
        if not session_id:
            print("❌ No session from OPTIONS")
            return
        
        # Step 2: Tool call WITH session
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream,application/json",
            "Mcp-Session-Id": session_id
        }
        
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": "search_products",
                "arguments": {
                    "query": "cricket bat",
                    "price_max": 2000,
                    "platform": "amazon"
                }
            }
        }
        
        resp = await client.post("http://localhost:8001/mcp", json=payload, headers=headers)
        print(f"Tool Status: {resp.status_code}")
        print(f"Tool Headers: {dict(resp.headers)}")
        print(f"Tool Response: {resp.text[:800]}")
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                print(f"✅ PRODUCTS: {data.get('result', {}).get('count', 0)}")
            except:
                print("📡 SSE stream detected")

asyncio.run(test_full_session())
