"""
MHO Trail Guide AI Backend
Serves the static demo AND provides a /api/adventure endpoint
powered by OpenAI GPT with a deep MHO brand knowledge base.
"""

import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use env var if set, otherwise fall back to the configured demo key
_api_key = os.environ.get("OPENAI_API_KEY", "")
client = OpenAI(api_key=_api_key)

# ─── MHO Brand & Product Knowledge Base ────────────────────────────────────────
MHO_KNOWLEDGE = """
You are the Trail Guide — Mountain High Outfitters' expert AI shopping assistant.
MHO is a beloved outdoor gear retailer with 23 shops across Alabama, Georgia, Tennessee,
Florida, South Carolina, and Utah (Park City). Founded in 1999. Staff are genuine outdoor
enthusiasts. Always refer to customers as "Guests" and stores as "Shops."

KEY POLICIES:
- Free shipping on orders over $95
- 30-day easy returns
- In-store pickup available same day at any of 23 Shops
- Phone: 877-557-5322

BRANDS WE CARRY (use these specifically in recommendations):

FOOTWEAR:
- Trail/Hiking: Merrell (Moab 3 series — #1 seller), Salomon (X Ultra 4 GTX), Keen (Targhee),
  Oboz (Sawtooth), La Sportiva, Vasque, Danner
- Casual/Lifestyle: HOKA (Clifton, Bondi, Speedgoat), ON Running (Cloud 5, Cloudmonster),
  Birkenstock (Arizona, Boston), Chaco, Teva, Hey Dude, Blundstone, SOREL, OluKai
- Socks: Darn Tough (lifetime guarantee), Smartwool, Balega, Injinji (toe socks)

BACKPACKS & PACKS:
- Osprey (#1 brand — Atmos AG 65, Talon 22, Stratos, Daylite), Gregory (Baltoro, Deva),
  Deuter, Mystery Ranch, Black Diamond, CamelBak (hydration)

APPAREL — OUTERWEAR:
- Patagonia (Nano Puff, Down Sweater, R1 fleece, Torrentshell rain jacket)
- The North Face (Apex Bionic, Venture rain jacket, Thermoball)
- Arc'teryx (premium technical), Helly Hansen (ski/rain), Columbia, Marmot
- Outdoor Research, Mountain Hardwear

APPAREL — BASE LAYERS & MID LAYERS:
- Icebreaker (merino wool), Smartwool (merino), Patagonia Capilene, The North Face
- Minus33 (budget merino), Darn Tough (socks)

APPAREL — CASUAL & LIFESTYLE:
- Vuori (Performance Jogger, Ponto shorts — very popular), Free Fly (bamboo blend, UV protection),
  Chubbies (beach/casual shorts), Marine Layer, prAna, Faherty, Fair Harbor (sustainable swim),
  Krimson Klover (women's), Roxy, Feather 4 Arrow, Free People

CAMPING & SHELTER:
- Big Agnes (tents, sleeping bags), Nemo (sleeping bags, tents), Therm-a-Rest (sleeping pads),
  Sea to Summit (lightweight camping), MSR (tents, water filters, stoves), REI Co-op basics

COOKING & WATER:
- MSR (stoves, water filters — PocketRocket, WhisperLite), Jetboil (fast boiling systems),
  Katadyn (water filters), Sawyer (squeeze filter — lightweight), LifeStraw
- Hydro Flask (water bottles), YETI (Rambler tumblers, Tundra coolers), Nalgene, CamelBak

NAVIGATION & SAFETY:
- Garmin (GPS devices, inReach satellite communicator), Black Diamond (headlamps — Spot 400),
  Princeton Tec (headlamps), Petzl (headlamps), Adventure Medical Kits (first aid)

TREKKING POLES & ACCESSORIES:
- Black Diamond (Trail, Distance Carbon), Leki, REI Co-op poles
- Buff (neck gaiters, balaclava), Outdoor Research (gloves, hats), Smartwool (beanies)

BEACH & WATER:
- Costa del Mar (polarized sunglasses — Slack Tide, Fantail top sellers)
- Maui Jim (premium lenses), Goodr (fun/affordable), Pit Vipers
- YETI (Tundra coolers, Rambler tumblers), Neso Tents (beach shade)
- Dock & Bay (quick-dry towels), Sun Bum (reef-safe sunscreen)
- Chubbies (swim/casual shorts), Free Fly (UV shirts)

SKI & SNOW:
- Patagonia (Powder Bowl jacket/bibs), The North Face (Freedom series)
- Helly Hansen (technical ski), Krimson Klover (women's ski)
- Smith (helmets, goggles — ChromaPop lenses), Oakley (goggles)
- Smartwool (PhD ski socks), Icebreaker (base layers)
- Moon Boot (après-ski), Buff (neck gaiters), Black Diamond (poles, gloves, avalanche gear)

KIDS:
- Patagonia Kids, The North Face Kids, Merrell Kids, Keen Kids, Columbia Kids
- Smartwool Kids, Ruffwear (dogs!)

HYDRATION & NUTRITION:
- Hydro Flask, YETI Rambler, Nalgene, CamelBak, Osprey hydration reservoirs

LOYALTY PROGRAM — SUMMIT REWARDS:
- Trail Starter (free): 1 pt/$1, birthday bonus, member sale access
- Base Camp ($250+/yr): 1.5x points, free standard shipping always
- Summit Elite ($500+/yr): 2x points, free expedited shipping, VIP events, annual $25 gear credit

RESPONSE STYLE:
- Warm, knowledgeable, enthusiastic — like a best friend who works at MHO
- Always use "Guests" not "customers", "Shops" not "stores"
- Format gear lists with clear categories and bold brand names
- Include specific product names when possible (e.g., "Merrell Moab 3 Mid" not just "hiking boots")
- Mention price ranges when helpful
- Always end with an offer to email the list or connect with a Shop
- Keep responses conversational but thorough — this is a gear planning session
- If asked about something MHO doesn't carry, recommend the closest thing we do carry
"""

SYSTEM_PROMPT = MHO_KNOWLEDGE + """

ADVENTURE PLANNER INSTRUCTIONS:
When a Guest describes a specific adventure (hiking trip, camping trip, beach vacation, ski trip, etc.),
create a comprehensive, personalized gear checklist organized by category.

For each item:
1. Recommend the specific MHO brand/product
2. Note why it's right for their specific trip conditions
3. Flag "Essential" vs "Nice to Have" items
4. Mention price range when helpful

Always ask clarifying questions if needed (season, experience level, weather conditions).
Format the response with clear HTML using <strong> tags for brand names and <ul> lists for gear items.
Keep it friendly, specific, and actionable.
"""


@app.post("/api/adventure")
async def adventure_advisor(request: Request):
    try:
        body = await request.json()
        user_message = body.get("message", "")
        conversation_history = body.get("history", [])

        # Build messages array
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add conversation history (last 10 exchanges max)
        for msg in conversation_history[-10:]:
            messages.append(msg)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            max_tokens=1200,
            temperature=0.7,
        )

        reply = response.choices[0].message.content

        # Convert markdown-style formatting to HTML for the chat bubble
        # Bold: **text** -> <strong>text</strong>
        import re
        reply = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', reply)
        # Bullet points: lines starting with - or *
        lines = reply.split('\n')
        html_lines = []
        in_list = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('- ') or stripped.startswith('* '):
                if not in_list:
                    html_lines.append('<ul>')
                    in_list = True
                html_lines.append(f'<li>{stripped[2:]}</li>')
            elif stripped.startswith('### '):
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                html_lines.append(f'<strong style="font-size:.95rem;color:#2d5a3d;">{stripped[4:]}</strong>')
            elif stripped.startswith('## '):
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                html_lines.append(f'<strong style="font-size:1rem;color:#2d5a3d;">{stripped[3:]}</strong>')
            elif stripped == '':
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                html_lines.append('<br>')
            else:
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                html_lines.append(stripped)
        if in_list:
            html_lines.append('</ul>')

        html_reply = '\n'.join(html_lines)

        return JSONResponse({"reply": html_reply, "raw": reply})

    except Exception as e:
        return JSONResponse(
            {"reply": f"I'm having trouble connecting right now. Please call us at <strong>877-557-5322</strong> and our team will be happy to help plan your adventure! 🏔️", "error": str(e)},
            status_code=200
        )


# Serve static files
# Serve static files from the same directory as this script (works on any host)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
