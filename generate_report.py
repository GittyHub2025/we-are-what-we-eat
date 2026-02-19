"""
we-are-what-we-eat · Phase 2 — Personalised Food Avatar PDF Report Generator
=============================================================================
Pulls every response from Supabase, scores the 6 Flavour Dimensions,
and renders a branded 2-page A4 PDF for each respondent.

Usage:
  pip install reportlab matplotlib supabase --break-system-packages
  python generate_report.py                  # all respondents
  python generate_report.py --limit 5        # first 5 only (preview)
  python generate_report.py --id <uuid>      # single respondent
  python generate_report.py --output reports # custom output folder

Output: reports/<id>.pdf  (one file per respondent)
"""

import os
import sys
import argparse
import io
import textwrap
from datetime import datetime

# ── CONFIGURATION ──────────────────────────────────────────────────────────────
SUPABASE_URL = "https://unhxcxaklhvefqveywmv.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVuaHhjeGFrbGh2ZWZxdmV5d212Iiw"
    "icm9sZSI6ImFub24iLCJpYXQiOjE3NzE0NjcxOTMsImV4cCI6MjA4NzA0MzE5M30"
    ".7N1HE-5jj9XuArcowsI-PZWTFqNO5JArE8rb0okswfY"
)

# ── BRAND PALETTE ──────────────────────────────────────────────────────────────
C = {
    "tangerine":  (1.00, 0.42, 0.21),   # #FF6B35
    "leaf":       (0.32, 0.72, 0.53),   # #52B788
    "sunshine":   (1.00, 0.85, 0.24),   # #FFD93D
    "berry":      (0.61, 0.36, 0.90),   # #9B5DE5
    "ocean":      (0.00, 0.73, 0.98),   # #00BBF9
    "blossom":    (1.00, 0.52, 0.63),   # #FF85A1
    "cloud":      (1.00, 0.97, 0.94),   # #FFF8F0
    "midnight":   (0.17, 0.17, 0.17),   # #2C2C2C
    "white":      (1.00, 1.00, 1.00),
    "lightgrey":  (0.93, 0.93, 0.93),
    "midgrey":    (0.55, 0.55, 0.55),
}

AVATAR_COLOR = {
    "sweet":       C["blossom"],
    "salty":       C["ocean"],
    "sour":        C["leaf"],
    "umami":       C["berry"],
    "crunchy":     C["tangerine"],
    "adventurous": C["sunshine"],
}

DIM_COLOR = {
    "Sweet":       C["blossom"],
    "Salty":       C["ocean"],
    "Sour":        C["leaf"],
    "Umami":       C["berry"],
    "Crunchy":     C["tangerine"],
    "Adventurous": C["sunshine"],
}

DIMS = ["Sweet", "Salty", "Sour", "Umami", "Crunchy", "Adventurous"]

# ── FLAVOUR SCORING (same as analyse.py) ───────────────────────────────────────
FLAVOUR_MAP = {
    "q5_flavour": {
        "Sweet":           {"sweet": 4},
        "Salty":           {"salty": 4},
        "Sour & Tangy":    {"sour": 4},
        "Savoury / Umami": {"umami": 4},
        "Slightly Bitter": {"umami": 2},
    },
    "q4_texture": {
        "Crunchy & Crispy": {"crunchy": 4},
        "Chewy":            {"crunchy": 1},
        "Soft & Creamy":    {"sweet": 1},
        "Fluffy & Airy":    {"sweet": 1},
        "Juicy & Wet":      {"sour": 1},
    },
    "q6_snack": {
        "Chips / Crisps":     {"salty": 2, "crunchy": 2},
        "Chocolate":          {"sweet": 2},
        "Biscuits / Cookies": {"sweet": 1, "crunchy": 1},
        "Fresh Fruit":        {"sour": 1, "adventurous": 1},
        "Seaweed Snack":      {"salty": 1, "crunchy": 2, "adventurous": 2},
        "Ice Cream":          {"sweet": 2},
        "Nuts or Seeds":      {"salty": 1, "crunchy": 2, "adventurous": 1},
    },
    "q9_new": {
        "Yes, definitely!":    {"adventurous": 3},
        "Maybe once or twice": {"adventurous": 2},
        "Not really":          {"adventurous": 0},
        "No":                  {"adventurous": 0},
    },
    "q10_new_food": {
        "Try it straight away!": {"adventurous": 3},
        "Ask what it is first":  {"adventurous": 2},
        "Depends how it looks":  {"adventurous": 1},
        "I usually avoid it":    {"adventurous": 0},
    },
    "q20_substitute": {
        "Definitely yes!":             {"adventurous": 2},
        "Maybe, if it tastes similar": {"adventurous": 1},
        "Not sure":                    {"adventurous": 0},
        "Probably not":                {"adventurous": 0},
    },
}

AVATAR_NAMES = {
    "sweet":       ("🍭 Sweet Seeker",   "You love sweet flavours and creamy textures!"),
    "salty":       ("🧂 Salt Captain",   "Bold salty and savoury tastes are your zone!"),
    "sour":        ("🍋 Sour Sparks",    "Tangy, sharp, and zingy — you love the tingle!"),
    "umami":       ("🍜 Umami Master",   "Deep savoury flavours are your happy place!"),
    "crunchy":     ("🥨 Crunch Hero",    "Texture is everything — you live for the crunch!"),
    "adventurous": ("🌍 Food Explorer",  "You're a natural adventurer who loves trying new things!"),
}

NEOPHOBIA_WEIGHTS = {
    "q9_new":       {"Yes, definitely!": 3, "Maybe once or twice": 2, "Not really": 1, "No": 0},
    "q10_new_food": {"Try it straight away!": 3, "Ask what it is first": 2,
                     "Depends how it looks": 1, "I usually avoid it": 0},
    "q20_substitute": {"Definitely yes!": 2, "Maybe, if it tastes similar": 1,
                       "Not sure": 0, "Probably not": 0},
}

# ── SUBSTITUTION SUGGESTIONS ───────────────────────────────────────────────────
# Personalised by dominant flavour + texture combo
SUBSTITUTIONS = {
    ("sweet",       "Soft & Creamy"):    ["Greek yogurt with honey & berries 🍓", "Banana nice cream (frozen banana blended) 🍌", "Mango coconut chia pudding 🥭"],
    ("sweet",       "Crunchy & Crispy"): ["Apple slices with peanut butter 🍎", "Granola with dried fruit 🌾", "Rice cakes with almond butter & banana 🍌"],
    ("sweet",       "Chewy"):            ["Dates stuffed with nut butter 🌴", "Oat energy balls with honey 🍯", "Dried mango strips (no added sugar) 🥭"],
    ("sweet",       "Fluffy & Airy"):    ["Whole-grain pancakes with fresh fruit 🥞", "Steamed pau with red bean filling 🫓", "Fruit smoothie bowl topped with granola 🍓"],
    ("sweet",       "Juicy & Wet"):      ["Fresh lychee or longan 🍈", "Watermelon with a pinch of salt 🍉", "Frozen grapes as a cool snack 🍇"],
    ("salty",       "Crunchy & Crispy"): ["Roasted edamame with sea salt 🫘", "Air-popped popcorn lightly salted 🍿", "Seaweed crisps (lower fat than chips) 🌿"],
    ("salty",       "Soft & Creamy"):    ["Edamame hummus with veggie sticks 🥦", "Miso soup with tofu & wakame 🍲", "Avocado on wholegrain toast 🥑"],
    ("salty",       "Chewy"):            ["Wholegrain pita with tzatziki 🫓", "Brown rice onigiri with pickled plum 🍙", "Baked pretzels with low-salt dip 🥨"],
    ("salty",       "Juicy & Wet"):      ["Cucumber with light soy dipping sauce 🥒", "Edamame pods straight from the bag 🫘", "Cherry tomatoes with a pinch of sea salt 🍅"],
    ("salty",       "Fluffy & Airy"):    ["Wholegrain crackers with cottage cheese 🧀", "Steamed egg with light soy sauce 🥚", "Low-sodium multigrain rice cakes 🌾"],
    ("sour",        "Juicy & Wet"):      ["Fresh kiwi or passion fruit 🥝", "Pomelo segments (tangy & refreshing) 🍊", "Homemade lemon barley water 🍋"],
    ("sour",        "Crunchy & Crispy"): ["Green mango salad (rojak-style) 🥭", "Pickled cucumber sticks 🥒", "Kimchi on wholegrain rice crackers 🌶️"],
    ("sour",        "Soft & Creamy"):    ["Plain yogurt with squeeze of lime 🍋", "Passion fruit yogurt parfait 🥝", "Chilled tofu with vinegar dressing 🍃"],
    ("sour",        "Chewy"):            ["Tamarind-glazed tempeh strips 🌿", "Yogurt-marinated chicken skewers 🍢", "Wholegrain sourdough with hummus 🫓"],
    ("sour",        "Fluffy & Airy"):    ["Lemon ricotta pancakes with berries 🍋", "Sourdough toast with avocado & lime 🥑", "Steamed fish with lemon & herbs 🐟"],
    ("umami",       "Soft & Creamy"):    ["Silken tofu with ponzu sauce 🍃", "Steamed egg custard (chawanmushi) 🥚", "Mushroom miso soup 🍄"],
    ("umami",       "Crunchy & Crispy"): ["Baked tempeh chips 🌿", "Roasted mushroom crisps 🍄", "Edamame & nori rice crackers 🌾"],
    ("umami",       "Chewy"):            ["Soba noodles with dashi broth 🍜", "Brown rice with furikake seasoning 🍙", "Mushroom & tofu stir-fry on brown rice 🍄"],
    ("umami",       "Juicy & Wet"):      ["Clear mushroom broth soup 🍲", "Steamed clams or mussels 🦪", "Tomato-based vegetable broth 🍅"],
    ("umami",       "Fluffy & Airy"):    ["Steamed bao with mushroom filling 🫓", "Fluffy Japanese-style egg omelette 🥚", "Soft tofu with bonito flakes & soy 🍃"],
    ("crunchy",     "Crunchy & Crispy"): ["Baked kale chips 🥬", "Roasted chickpeas (spiced) 🫘", "Mixed nuts & seeds trail mix 🌰"],
    ("crunchy",     "Chewy"):            ["Celery & carrot sticks with hummus 🥕", "Whole almonds with dark chocolate 🍫", "Toasted wholegrain crispbread 🌾"],
    ("crunchy",     "Soft & Creamy"):    ["Veggie sticks with guacamole 🥑", "Apple slices with yogurt dip 🍎", "Cucumber rounds with cream cheese 🥒"],
    ("crunchy",     "Juicy & Wet"):      ["Jicama (bangkuang) sticks with lime 🌿", "Water chestnuts stir-fried lightly 🌱", "Lotus root chips (baked) 🌸"],
    ("crunchy",     "Fluffy & Airy"):    ["Rice crackers with avocado 🌾", "Baked wholegrain puffs 🫧", "Air-popped corn dusted with nutritional yeast 🍿"],
    ("adventurous", "Crunchy & Crispy"): ["Oven-baked cricket protein snacks 🦗", "Roasted lotus seeds 🌸", "Spirulina-dusted popcorn 🌿"],
    ("adventurous", "Soft & Creamy"):    ["Jackfruit pulled 'pork' tacos 🌮", "Purple sweet potato hummus 💜", "Fermented foods sampler — kimchi, miso, kefir 🥬"],
    ("adventurous", "Chewy"):            ["Açaí bowl with exotic toppings 🫐", "Kelp noodle salad 🌿", "Tempeh rendang on brown rice 🍛"],
    ("adventurous", "Juicy & Wet"):      ["Dragon fruit bowl 🐉", "Starfruit & lime juice cooler ⭐", "Pomegranate & rose water smoothie 🌹"],
    ("adventurous", "Fluffy & Airy"):    ["Pandan chiffon cake (naturally green!) 🌿", "Blue pea flower steamed buns 💙", "Matcha soft-serve with black sesame 🍵"],
}

def get_substitutions(dominant, texture):
    """Get 3 personalised substitution suggestions."""
    key = (dominant, texture)
    if key in SUBSTITUTIONS:
        return SUBSTITUTIONS[key]
    # Fallback: use dominant only, pick any texture
    for k, v in SUBSTITUTIONS.items():
        if k[0] == dominant:
            return v
    return [
        "More colourful fruits and vegetables 🌈",
        "Wholegrain versions of your favourite foods 🌾",
        "Water or low-sugar drinks instead of sodas 💧",
    ]


def score_flavour_profile(row):
    """Score a single respondent across 6 flavour dimensions."""
    dims = {d.lower(): 0 for d in DIMS}
    for col, mapping in FLAVOUR_MAP.items():
        val = row.get(col)
        if val and val in mapping:
            for dim, pts in mapping[val].items():
                dims[dim] += pts
    cuisines = row.get("q18_cuisine") or []
    dims["adventurous"] += min(len(cuisines), 4)
    adv_foods = row.get("q19_adv") or []
    dims["adventurous"] += min(len([f for f in adv_foods if f != "None of these yet!"]), 4)
    dims = {k: min(v, 10) for k, v in dims.items()}
    dominant = max(dims, key=dims.get)
    name, desc = AVATAR_NAMES.get(dominant, ("🌱 Food Friend", "You have a balanced palate!"))
    neo_score = sum(NEOPHOBIA_WEIGHTS[q].get(row.get(q, ""), 0) for q in NEOPHOBIA_WEIGHTS)
    return {**dims, "dominant": dominant, "avatar_name": name, "avatar_desc": desc,
            "neo_score": neo_score}


# ── CHART GENERATION ───────────────────────────────────────────────────────────

def make_bar_chart(profile, dominant):
    """Render a horizontal bar chart; return PNG bytes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    labels = DIMS
    values = [profile[d.lower()] for d in DIMS]
    colors = [DIM_COLOR[d] for d in DIMS]

    fig, ax = plt.subplots(figsize=(6.2, 2.8))
    fig.patch.set_facecolor("#FFF8F0")
    ax.set_facecolor("#FFF8F0")

    bars = ax.barh(labels[::-1], values[::-1], color=colors[::-1],
                   height=0.62, edgecolor="white", linewidth=1.5)

    # Value labels
    for bar, val in zip(bars, values[::-1]):
        ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height() / 2,
                f"{val}/10", va="center", ha="left",
                fontsize=10, fontweight="bold",
                color="#2C2C2C", fontfamily="DejaVu Sans")

    ax.set_xlim(0, 12)
    ax.set_xlabel("Score (out of 10)", fontsize=9, color="#555555")
    ax.tick_params(axis="y", labelsize=10, colors="#2C2C2C")
    ax.tick_params(axis="x", labelsize=8, colors="#888888")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#DDDDDD")
    ax.spines["bottom"].set_color("#DDDDDD")
    ax.set_title("Your Flavour DNA Profile", fontsize=12, fontweight="bold",
                 color="#2C2C2C", pad=10, fontfamily="DejaVu Sans")
    ax.grid(axis="x", color="#EEEEEE", linewidth=0.8, linestyle="--")
    ax.set_axisbelow(True)

    plt.tight_layout(pad=0.8)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor="#FFF8F0")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ── PDF RENDERING ──────────────────────────────────────────────────────────────

def hex_to_rl(color_tuple):
    """reportlab Color from 0-1 RGB tuple."""
    from reportlab.lib.colors import Color
    return Color(*color_tuple)


def draw_page1(c, row, profile, chart_png_bytes, page_w, page_h):
    """Draw the Avatar & Flavour DNA page."""
    from reportlab.lib.colors import Color
    from reportlab.lib.utils import ImageReader

    dominant = profile["dominant"]
    avatar_color = hex_to_rl(AVATAR_COLOR.get(dominant, C["leaf"]))
    avatar_name_raw = profile["avatar_name"]   # e.g. "🍭 Sweet Seeker"
    avatar_desc = profile["avatar_desc"]

    # Strip emoji from avatar name for safe PDF rendering
    import re
    avatar_name_clean = re.sub(r'[^\x00-\x7F]+', '', avatar_name_raw).strip()
    # Keep emoji label separately
    emoji_map = {
        "sweet": "Sweet Seeker", "salty": "Salt Captain", "sour": "Sour Sparks",
        "umami": "Umami Master", "crunchy": "Crunch Hero", "adventurous": "Food Explorer"
    }
    avatar_label = emoji_map.get(dominant, "Food Friend")

    # ── HEADER BANNER ──────────────────────────────────────────────────────────
    banner_h = 110
    # Rainbow gradient: draw 6 vertical strips
    strip_w = page_w / 6
    strip_colors = [C["tangerine"], C["sunshine"], C["leaf"], C["ocean"], C["berry"], C["blossom"]]
    for i, sc in enumerate(strip_colors):
        c.setFillColor(hex_to_rl(sc))
        c.rect(i * strip_w, page_h - banner_h, strip_w + 1, banner_h, fill=1, stroke=0)

    # Semi-transparent overlay for text legibility
    c.setFillColor(Color(0, 0, 0, alpha=0.28))
    c.rect(0, page_h - banner_h, page_w, banner_h, fill=1, stroke=0)

    c.setFillColor(hex_to_rl(C["white"]))
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(page_w / 2, page_h - 42, "We Are What We Eat")
    c.setFont("Helvetica", 11)
    c.drawCentredString(page_w / 2, page_h - 62, "Isaac's Food Science Project  ·  Singapore 2026")
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(page_w / 2, page_h - 80, "Your Personalised Food Avatar Report")

    y = page_h - banner_h

    # ── AVATAR CARD ────────────────────────────────────────────────────────────
    card_top = y - 14
    card_h = 110
    margin = 36
    card_w = page_w - 2 * margin

    # Card shadow
    c.setFillColor(Color(0, 0, 0, alpha=0.08))
    c.roundRect(margin + 3, card_top - card_h - 3, card_w, card_h, 12, fill=1, stroke=0)
    # Card background
    c.setFillColor(hex_to_rl(C["white"]))
    c.roundRect(margin, card_top - card_h, card_w, card_h, 12, fill=1, stroke=0)
    # Left color accent
    c.setFillColor(avatar_color)
    c.roundRect(margin, card_top - card_h, 8, card_h, 4, fill=1, stroke=0)

    # Avatar emoji circle
    circle_x = margin + 8 + 38
    circle_y = card_top - card_h / 2
    c.setFillColor(avatar_color)
    c.circle(circle_x, circle_y, 30, fill=1, stroke=0)

    avatar_emoji_text = {
        "sweet": "SWEET", "salty": "SALTY", "sour": "SOUR",
        "umami": "UMAMI", "crunchy": "CRUNCH", "adventurous": "EXPLORER"
    }
    c.setFillColor(hex_to_rl(C["white"]))
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(circle_x, circle_y - 3, avatar_emoji_text.get(dominant, "FOOD"))

    # Avatar text
    text_x = margin + 8 + 30 + 30 + 12
    c.setFillColor(hex_to_rl(C["midnight"]))
    c.setFont("Helvetica-Bold", 17)
    c.drawString(text_x, card_top - 32, avatar_label)

    c.setFillColor(avatar_color)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(text_x, card_top - 50, f"YOUR FOOD AVATAR")

    # Wrap avatar_desc
    desc_clean = re.sub(r'[^\x00-\x7F]+', '', avatar_desc).strip()
    c.setFillColor(hex_to_rl(C["midgrey"]))
    c.setFont("Helvetica", 10)
    c.drawString(text_x, card_top - 68, desc_clean)

    # Level / who badge
    level = row.get("q2_level", "")
    who = row.get("q1_who", "")
    badge_text = f"{level}  ·  {who}" if level and who else level or who
    if badge_text:
        c.setFillColor(hex_to_rl(C["lightgrey"]))
        badge_w = c.stringWidth(badge_text, "Helvetica", 8) + 16
        c.roundRect(text_x, card_top - 95, badge_w, 16, 4, fill=1, stroke=0)
        c.setFillColor(hex_to_rl(C["midgrey"]))
        c.setFont("Helvetica", 8)
        c.drawString(text_x + 8, card_top - 87, badge_text)

    y = card_top - card_h - 20

    # ── BAR CHART ─────────────────────────────────────────────────────────────
    chart_label_y = y - 4
    c.setFillColor(hex_to_rl(C["midnight"]))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, chart_label_y, "Flavour DNA Chart")

    # Thin accent line under label
    c.setStrokeColor(avatar_color)
    c.setLineWidth(2)
    c.line(margin, chart_label_y - 4, margin + 120, chart_label_y - 4)

    chart_img = ImageReader(io.BytesIO(chart_png_bytes))
    chart_h_pt = 175
    chart_w_pt = page_w - 2 * margin
    c.drawImage(chart_img, margin, y - 16 - chart_h_pt, width=chart_w_pt, height=chart_h_pt,
                preserveAspectRatio=True, mask="auto")

    y = y - 16 - chart_h_pt - 14

    # ── NEOPHOBIA METER ────────────────────────────────────────────────────────
    neo = profile["neo_score"]
    neo_label = "Neophobic" if neo <= 2 else ("Moderate" if neo <= 5 else "Adventurous!")
    neo_color = C["blossom"] if neo <= 2 else (C["sunshine"] if neo <= 5 else C["leaf"])

    c.setFillColor(hex_to_rl(C["midnight"]))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "Food Adventurousness Score")

    bar_total_w = page_w - 2 * margin - 120
    bar_h2 = 14
    bar_x = margin
    bar_y = y - 22

    # Background bar
    c.setFillColor(hex_to_rl(C["lightgrey"]))
    c.roundRect(bar_x, bar_y, bar_total_w, bar_h2, 6, fill=1, stroke=0)
    # Filled portion
    fill_w = max(18, int(neo / 8 * bar_total_w))
    c.setFillColor(hex_to_rl(neo_color))
    c.roundRect(bar_x, bar_y, fill_w, bar_h2, 6, fill=1, stroke=0)
    # Label
    c.setFillColor(hex_to_rl(C["midnight"]))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(bar_x + bar_total_w + 10, bar_y + 3, f"{neo}/8  {neo_label}")

    # Scale labels
    c.setFont("Helvetica", 7)
    c.setFillColor(hex_to_rl(C["midgrey"]))
    c.drawString(bar_x, bar_y - 10, "Cautious")
    c.drawRightString(bar_x + bar_total_w, bar_y - 10, "Adventurous")

    y = bar_y - 24

    # ── FOOTER ─────────────────────────────────────────────────────────────────
    _draw_footer(c, page_w, "Page 1 of 2")


def draw_page2(c, row, profile, page_w, page_h):
    """Draw the Personalised Insights & Substitutions page."""
    from reportlab.lib.colors import Color
    import re

    dominant = profile["dominant"]
    avatar_color = hex_to_rl(AVATAR_COLOR.get(dominant, C["leaf"]))
    texture = row.get("q4_texture", "")
    subs = get_substitutions(dominant, texture)

    # ── HEADER (slimmer) ──────────────────────────────────────────────────────
    banner_h = 62
    strip_w = page_w / 6
    strip_colors = [C["tangerine"], C["sunshine"], C["leaf"], C["ocean"], C["berry"], C["blossom"]]
    for i, sc in enumerate(strip_colors):
        c.setFillColor(hex_to_rl(sc))
        c.rect(i * strip_w, page_h - banner_h, strip_w + 1, banner_h, fill=1, stroke=0)
    c.setFillColor(Color(0, 0, 0, alpha=0.28))
    c.rect(0, page_h - banner_h, page_w, banner_h, fill=1, stroke=0)

    c.setFillColor(hex_to_rl(C["white"]))
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(page_w / 2, page_h - 30, "Your Personalised Food Insights")
    c.setFont("Helvetica", 9)
    c.drawCentredString(page_w / 2, page_h - 48, "We Are What We Eat  ·  Isaac's Food Science Project  ·  Singapore 2026")

    y = page_h - banner_h - 22
    margin = 36
    col_w = page_w - 2 * margin

    # ── SECTION: HEALTHY SWAPS ────────────────────────────────────────────────
    y = _section_header(c, "Healthy Swaps Made For You 🥗", y, margin, col_w, avatar_color)
    y -= 6

    # Intro sentence
    flavour_label = row.get("q5_flavour", "great flavour")
    texture_label = row.get("q4_texture", "your favourite texture")
    intro = (f"Because you love {flavour_label.lower()} flavours and {texture_label.lower()} textures, "
             f"here are 3 healthier alternatives that still feel familiar and delicious!")
    intro_clean = re.sub(r'[^\x00-\x7F]+', '', intro)
    y = _wrapped_text(c, intro_clean, margin, y, col_w, 9, C["midgrey"])
    y -= 8

    # 3 swap cards
    swap_colors = [C["leaf"], C["ocean"], C["sunshine"]]
    for i, sub in enumerate(subs[:3]):
        sub_clean = re.sub(r'[^\x00-\x7F]+', '', sub).strip()
        card_h = 36
        sc = hex_to_rl(swap_colors[i % 3])

        # Card
        c.setFillColor(hex_to_rl(C["white"]))
        c.roundRect(margin, y - card_h, col_w, card_h, 8, fill=1, stroke=0)
        c.setStrokeColor(sc)
        c.setLineWidth(1.2)
        c.roundRect(margin, y - card_h, col_w, card_h, 8, fill=0, stroke=1)

        # Number circle
        c.setFillColor(sc)
        c.circle(margin + 20, y - card_h / 2, 11, fill=1, stroke=0)
        c.setFillColor(hex_to_rl(C["white"]))
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(margin + 20, y - card_h / 2 - 3.5, str(i + 1))

        # Text
        c.setFillColor(hex_to_rl(C["midnight"]))
        c.setFont("Helvetica", 10)
        c.drawString(margin + 38, y - card_h / 2 - 3.5, sub_clean)

        y -= card_h + 6

    y -= 10

    # ── SECTION: WHY IT WORKS ─────────────────────────────────────────────────
    y = _section_header(c, "Why This Works — Isaac's Research 🔬", y, margin, col_w, avatar_color)
    y -= 6

    why_text = (
        "Isaac's project studies how children can eat healthier by swapping foods that share "
        "the same texture, flavour, or look. This is called 'substitution via similarity'. "
        "Your swap suggestions above were chosen because they match your personal Flavour DNA — "
        "so they should feel just as satisfying as your current favourites!"
    )
    y = _wrapped_text(c, why_text, margin, y, col_w, 9.5, C["midnight"])
    y -= 14

    # ── SECTION: YOUR ANSWERS AT A GLANCE ────────────────────────────────────
    y = _section_header(c, "Your Answers at a Glance", y, margin, col_w, avatar_color)
    y -= 8

    qa_pairs = [
        ("Favourite texture",       row.get("q4_texture", "—")),
        ("Favourite flavour",       row.get("q5_flavour", "—")),
        ("Favourite snack",         row.get("q6_snack",   "—")),
        ("Tried new food recently", row.get("q9_new",     "—")),
        ("Open to healthy swaps",   row.get("q20_substitute", "—")),
        ("What 'healthy' means",    ", ".join(row.get("q24_healthy") or []) or "—"),
    ]

    col1_w = 175
    row_h = 20
    for q_label, q_val in qa_pairs:
        # Subtle row stripe
        c.setFillColor(hex_to_rl(C["lightgrey"]))
        c.rect(margin, y - row_h + 4, col_w, row_h, fill=1, stroke=0)

        c.setFillColor(hex_to_rl(C["midgrey"]))
        c.setFont("Helvetica", 8.5)
        c.drawString(margin + 6, y - 10, q_label)

        val_clean = re.sub(r'[^\x00-\x7F]+', '', str(q_val)).strip()
        c.setFillColor(hex_to_rl(C["midnight"]))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(margin + col1_w, y - 10, val_clean[:68])

        y -= row_h

    y -= 12

    # ── SECTION: FUN FOOD FACT ────────────────────────────────────────────────
    y = _section_header(c, "Did You Know? 💡", y, margin, col_w, avatar_color)
    y -= 8

    fun_facts = {
        "sweet":       "Bananas are berries, but strawberries are NOT! Botanically, a banana counts as a berry because it develops from a single flower.",
        "salty":       "Your tongue has about 10,000 taste buds! Salty taste helps us detect minerals that our bodies need to function.",
        "sour":        "Sour taste comes from acids. Vitamin C — the healthy stuff in fruits — is actually ascorbic ACID, which is why citrus tastes tangy!",
        "umami":       "Umami was only officially named in 1908 by Japanese scientist Kikunae Ikeda. It comes from glutamate, found in mushrooms, seaweed and cheese.",
        "crunchy":     "The sound of crunchiness actually affects how we taste food! Scientists found people rate crisps as tastier when they hear the crunch louder.",
        "adventurous": "The world has over 20,000 edible plant species — but only about 200 are commonly eaten. You have a whole world of flavours to explore!",
    }
    fact = fun_facts.get(dominant, "Every person's taste is unique — no two Flavour DNA profiles are exactly the same!")
    y = _wrapped_text(c, fact, margin, y, col_w, 9.5, C["midnight"], italic=True)

    # ── FOOTER ─────────────────────────────────────────────────────────────────
    _draw_footer(c, page_w, "Page 2 of 2")


def _section_header(c, title, y, margin, col_w, accent_color):
    """Draw a section heading with accent underline. Returns new y."""
    import re
    title_clean = re.sub(r'[^\x00-\x7F\U0001F300-\U0001FFFF]+', title, title)
    title_clean = re.sub(r'[^\x00-\x7F]+', '', title).strip()
    c.setFillColor(hex_to_rl(C["midnight"]))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, title_clean)
    c.setStrokeColor(accent_color)
    c.setLineWidth(2)
    title_w = c.stringWidth(title_clean, "Helvetica-Bold", 11)
    c.line(margin, y - 5, margin + title_w + 4, y - 5)
    return y - 16


def _wrapped_text(c, text, x, y, max_w, font_size, color_tuple, italic=False):
    """Draw wrapped text. Returns new y position."""
    font = "Helvetica-Oblique" if italic else "Helvetica"
    c.setFont(font, font_size)
    c.setFillColor(hex_to_rl(color_tuple))
    chars_per_line = int(max_w / (font_size * 0.52))
    lines = textwrap.wrap(text, width=chars_per_line)
    line_h = font_size * 1.55
    for line in lines:
        c.drawString(x, y, line)
        y -= line_h
    return y


def _draw_footer(c, page_w, page_label):
    """Draw footer bar."""
    c.setFillColor(hex_to_rl(C["midnight"]))
    c.rect(0, 0, page_w, 28, fill=1, stroke=0)
    c.setFillColor(hex_to_rl(C["white"]))
    c.setFont("Helvetica", 7.5)
    c.drawString(18, 10, "Isaac's Project: We Are What We Eat  ·  P3–P6 Longitudinal Study  ·  Singapore 2026")
    c.drawRightString(page_w - 18, 10, page_label)


# ── MAIN ────────────────────────────────────────────────────────────────────────

def generate_pdf(row, out_dir):
    """Generate a 2-page PDF for a single respondent. Returns output path."""
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4

    profile = score_flavour_profile(row)
    chart_png = make_bar_chart(profile, profile["dominant"])

    row_id = str(row.get("id", "unknown"))[:8]
    level = row.get("q2_level", "XX")
    fname = f"{out_dir}/{level}_{row_id}.pdf"

    page_w, page_h = A4   # 595.27 x 841.89 pts
    c = rl_canvas.Canvas(fname, pagesize=A4)
    c.setTitle("We Are What We Eat — Your Food Avatar Report")
    c.setAuthor("Isaac's Project 2026")

    # Page 1
    draw_page1(c, row, profile, chart_png, page_w, page_h)
    c.showPage()

    # Page 2
    draw_page2(c, row, profile, page_w, page_h)
    c.save()

    return fname


def main():
    parser = argparse.ArgumentParser(description="Generate personalised Food Avatar PDF reports")
    parser.add_argument("--limit",  type=int,  default=None, help="Max number of reports to generate")
    parser.add_argument("--id",     type=str,  default=None, help="Generate report for a single respondent UUID")
    parser.add_argument("--output", type=str,  default="reports", help="Output folder (default: reports/)")
    args = parser.parse_args()

    try:
        from supabase import create_client
    except ImportError:
        print("Run: pip install supabase --break-system-packages")
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)
    print(f"🔌 Connecting to Supabase…")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    if args.id:
        resp = client.table("survey_responses").select("*").eq("id", args.id).execute()
    else:
        resp = client.table("survey_responses").select("*").order("submitted_at").execute()

    rows = resp.data
    if not rows:
        print("⚠️  No responses found.")
        return

    if args.limit:
        rows = rows[:args.limit]

    total = len(rows)
    print(f"📋 Generating {total} report(s) → {args.output}/\n")

    for i, row in enumerate(rows, 1):
        try:
            path = generate_pdf(row, args.output)
            profile = score_flavour_profile(row)
            avatar = profile["avatar_name"]
            avatar_clean = avatar.encode("ascii", "ignore").decode()
            level = row.get("q2_level", "?")
            print(f"  [{i:>3}/{total}] {level}  {avatar_clean:<20}  → {os.path.basename(path)}")
        except Exception as e:
            print(f"  [{i:>3}/{total}] ERROR for {row.get('id','?')}: {e}")

    print(f"\n✅ Done! {total} PDF(s) saved to ./{args.output}/")
    print(f"   Open any PDF to see the personalised Food Avatar Report.")


if __name__ == "__main__":
    main()
