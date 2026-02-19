"""
we-are-what-we-eat · Survey Analysis Script
============================================
Pulls all responses from Supabase and produces:
  1. Console summary (quick overview)
  2. responses.csv   — flat export of every response
  3. summary.json    — aggregated counts for every question
  4. flavour_profiles.csv — per-respondent flavour profile scores

Usage:
  pip install supabase pandas tabulate
  python analyse.py

  # Optional flags:
  python analyse.py --level P3          # filter by school level
  python analyse.py --export-emails     # list emails (for report mailout)
  python analyse.py --since 2026-03-01  # only responses after this date
"""

import sys
import json
import argparse
from datetime import datetime
from collections import Counter

# ── CONFIGURATION ──────────────────────────────────────────────────────────────
SUPABASE_URL = "https://unhxcxaklhvefqveywmv.supabase.co"
SUPABASE_KEY = "sb_publishable_KU1Umj62XGDgTzQhR6MZAw_OuyB-WwT"

# ── IMPORTS ────────────────────────────────────────────────────────────────────
try:
    from supabase import create_client
except ImportError:
    print("Run: pip install supabase")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("Run: pip install pandas")
    sys.exit(1)

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


# ── HELPERS ────────────────────────────────────────────────────────────────────

def pct(n, total):
    return f"{round(100*n/total)}%" if total else "—"

def print_header(title):
    print(f"\n{'═'*60}")
    print(f"  {title}")
    print(f"{'═'*60}")

def print_section(title):
    print(f"\n  ── {title} ──")

def top_choices(series, n=5):
    """Returns top N value counts as a list of (value, count, pct) tuples."""
    counts = series.dropna().value_counts()
    total  = counts.sum()
    return [(v, c, pct(c, total)) for v, c in counts.head(n).items()]

def explode_array_col(df, col):
    """Explode a column that contains Python lists (from Supabase text[] arrays)."""
    s = df[col].explode()
    return s[s.notna() & (s != "")]


# ── FLAVOUR PROFILE SCORING ─────────────────────────────────────────────────────
# Maps survey answers to 6 Flavour Dimensions (0–10 scale each)
# Dimensions: Sweet · Salty · Sour · Umami · Crunchy · Adventurous

FLAVOUR_MAP = {
    # Q5 primary flavour → dimension +4 pts
    "q5_flavour": {
        "Sweet":          {"sweet": 4},
        "Salty":          {"salty": 4},
        "Sour & Tangy":   {"sour": 4},
        "Savoury / Umami":{"umami": 4},
        "Slightly Bitter":{"umami": 2},
    },
    # Q4 texture → crunchy dimension
    "q4_texture": {
        "Crunchy & Crispy": {"crunchy": 4},
        "Chewy":            {"crunchy": 1},
        "Soft & Creamy":    {"sweet": 1},
        "Fluffy & Airy":    {"sweet": 1},
        "Juicy & Wet":      {"sour": 1},
    },
    # Q6 snack
    "q6_snack": {
        "Chips / Crisps":   {"salty": 2, "crunchy": 2},
        "Chocolate":        {"sweet": 2},
        "Biscuits / Cookies":{"sweet": 1, "crunchy": 1},
        "Fresh Fruit":      {"sour": 1, "adventurous": 1},
        "Seaweed Snack":    {"salty": 1, "crunchy": 2, "adventurous": 2},
        "Ice Cream":        {"sweet": 2},
        "Nuts or Seeds":    {"salty": 1, "crunchy": 2, "adventurous": 1},
    },
    # Q9 trying new foods → adventurous
    "q9_new": {
        "Yes, definitely!":         {"adventurous": 3},
        "Maybe once or twice":      {"adventurous": 2},
        "Not really":               {"adventurous": 0},
        "No":                       {"adventurous": 0},
    },
    # Q10 reaction to unfamiliar food → adventurous
    "q10_new_food": {
        "Try it straight away!":          {"adventurous": 3},
        "Ask what it is first":           {"adventurous": 2},
        "Depends how it looks":           {"adventurous": 1},
        "I usually avoid it":             {"adventurous": 0},
    },
    # Q20 substitute willingness → adventurous
    "q20_substitute": {
        "Definitely yes!":              {"adventurous": 2},
        "Maybe, if it tastes similar":  {"adventurous": 1},
        "Not sure":                     {"adventurous": 0},
        "Probably not":                 {"adventurous": 0},
    },
}

AVATAR_NAMES = {
    # Dominant dimension → avatar
    "sweet":       ("🍭 Sweet Seeker",   "You love sweet flavours and creamy textures!"),
    "salty":       ("🧂 Salt Captain",   "Bold salty and savoury tastes are your zone!"),
    "sour":        ("🍋 Sour Sparks",    "Tangy, sharp, and zingy — you love the tingle!"),
    "umami":       ("🍜 Umami Master",   "Deep savoury flavours are your happy place!"),
    "crunchy":     ("🥨 Crunch Hero",    "Texture is everything — you live for the crunch!"),
    "adventurous": ("🌍 Food Explorer",  "You're a natural adventurer who loves trying new things!"),
}

def score_flavour_profile(row):
    """Score a single respondent's flavour dimensions."""
    dims = {"sweet": 0, "salty": 0, "sour": 0, "umami": 0, "crunchy": 0, "adventurous": 0}
    for col, mapping in FLAVOUR_MAP.items():
        val = row.get(col)
        if val and val in mapping:
            for dim, pts in mapping[val].items():
                dims[dim] += pts
    # Cuisine diversity → adventurous bonus
    cuisines = row.get("q18_cuisine") or []
    dims["adventurous"] += min(len(cuisines), 4)
    # Adventurous foods tried → adventurous bonus
    adv_foods = row.get("q19_adv") or []
    dims["adventurous"] += min(len([f for f in adv_foods if f != "None of these yet!"]), 4)
    # Cap at 10
    dims = {k: min(v, 10) for k, v in dims.items()}
    dominant = max(dims, key=dims.get)
    name, desc = AVATAR_NAMES.get(dominant, ("🌱 Food Friend", "You have a balanced palate!"))
    return {**dims, "dominant": dominant, "avatar_name": name, "avatar_desc": desc}


# ── MAIN ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Analyse We Are What We Eat survey data")
    parser.add_argument("--level",         help="Filter by school level (e.g. P3)", default=None)
    parser.add_argument("--since",         help="Filter responses after date (YYYY-MM-DD)", default=None)
    parser.add_argument("--export-emails", action="store_true", help="Print email list")
    parser.add_argument("--output-dir",    help="Directory for output files", default=".")
    args = parser.parse_args()

    # ── Connect & Fetch ──────────────────────────────────────────────────────
    print("🔌 Connecting to Supabase…")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    query = client.table("survey_responses").select("*")
    if args.level:
        query = query.eq("q2_level", args.level)
    if args.since:
        query = query.gte("submitted_at", args.since)

    response = query.order("submitted_at", desc=False).execute()
    rows = response.data

    if not rows:
        print("⚠️  No responses found (check your filters).")
        return

    df = pd.DataFrame(rows)
    df["submitted_at"] = pd.to_datetime(df["submitted_at"])
    N = len(df)

    # ── CONSOLE SUMMARY ──────────────────────────────────────────────────────
    print_header(f"WE ARE WHAT WE EAT — Survey Analysis  ({N} responses)")

    level_filter = f" [filtered: {args.level}]" if args.level else ""
    date_range = f"{df['submitted_at'].min().date()} → {df['submitted_at'].max().date()}"
    print(f"  📅 Date range : {date_range}{level_filter}")
    print(f"  📊 Total      : {N} complete responses")

    emails_with_data = df["email"].dropna()
    emails_with_data = emails_with_data[emails_with_data.str.strip() != ""]
    print(f"  📧 With email : {len(emails_with_data)} ({pct(len(emails_with_data), N)})")

    # ── Section 1: Demographics ──────────────────────────────────────────────
    print_section("SECTION 1 · Demographics")
    for col, label in [("q2_level","School Level"), ("q3_gender","Gender"), ("q1_who","Who filled in")]:
        vc = df[col].value_counts()
        rows_out = [(v, c, pct(c,N)) for v, c in vc.items()]
        print(f"\n  {label}:")
        for v, c, p in rows_out:
            bar = "█" * int(c/N*20)
            print(f"    {v:<35} {c:>4}  {p:>5}  {bar}")

    # ── Section 2: Flavour DNA ────────────────────────────────────────────────
    print_section("SECTION 2 · Flavour DNA")
    for col, label in [
        ("q4_texture","Favourite Texture"),
        ("q5_flavour","Favourite Flavour"),
        ("q6_snack",  "Favourite Snack"),
        ("q7_spicy",  "Spicy Tolerance"),
        ("q8_fruit",  "Favourite Fruit"),
        ("q9_new",    "Tried new food last month"),
        ("q10_new_food","Reaction to unfamiliar food"),
    ]:
        print(f"\n  {label}:")
        for v, c, p in top_choices(df[col], n=8):
            bar = "█" * int(c/N*20)
            print(f"    {str(v):<40} {c:>4}  {p:>5}  {bar}")

    # ── Section 3: Eating Habits ──────────────────────────────────────────────
    print_section("SECTION 3 · Eating Habits")
    for col, label in [
        ("q11_veg","Vegetables yesterday"),
        ("q12_drinks","Sugary drinks yesterday"),
        ("q13_fried","Fried food last week"),
        ("q14_family","Family dinners last week"),
        ("q16_breakfast","Breakfast days last week"),
        ("q17_school","School food type"),
    ]:
        print(f"\n  {label}:")
        for v, c, p in top_choices(df[col], n=6):
            bar = "█" * int(c/N*20)
            print(f"    {str(v):<40} {c:>4}  {p:>5}  {bar}")

    # ── Section 4: Food Explorer ──────────────────────────────────────────────
    print_section("SECTION 4 · Food Explorer")

    print("\n  Cuisines tried (multi-select):")
    cuisine_counts = explode_array_col(df, "q18_cuisine").value_counts()
    for v, c in cuisine_counts.items():
        bar = "█" * int(c/N*20)
        print(f"    {str(v):<30} {c:>4}  {pct(c,N):>5}  {bar}")

    print("\n  Adventurous foods tried:")
    adv_counts = explode_array_col(df, "q19_adv").value_counts()
    for v, c in adv_counts.items():
        bar = "█" * int(c/N*20)
        print(f"    {str(v):<30} {c:>4}  {pct(c,N):>5}  {bar}")

    for col, label in [("q20_substitute","Open to healthy substitutes"),
                       ("q21_intro","Food introduced by"),
                       ("q22_convo","Family food conversations")]:
        print(f"\n  {label}:")
        for v, c, p in top_choices(df[col], n=6):
            bar = "█" * int(c/N*20)
            print(f"    {str(v):<40} {c:>4}  {p:>5}  {bar}")

    # ── Section 5: Health Awareness ───────────────────────────────────────────
    print_section("SECTION 5 · Health Awareness")

    for col, label in [("q23_feel","Post-meal feeling"), ("q25_improve","One thing to improve")]:
        print(f"\n  {label}:")
        for v, c, p in top_choices(df[col], n=6):
            bar = "█" * int(c/N*20)
            print(f"    {str(v):<40} {c:>4}  {p:>5}  {bar}")

    print("\n  'Healthy eating' means (multi-select):")
    healthy_counts = explode_array_col(df, "q24_healthy").value_counts()
    for v, c in healthy_counts.items():
        bar = "█" * int(c/N*20)
        print(f"    {str(v):<45} {c:>4}  {pct(c,N):>5}  {bar}")

    # ── Flavour Profiles ──────────────────────────────────────────────────────
    print_section("FLAVOUR PROFILES · Avatar Distribution")
    profile_rows = df.apply(score_flavour_profile, axis=1)
    profiles_df  = pd.DataFrame(list(profile_rows))

    avatar_counts = profiles_df["avatar_name"].value_counts()
    for avatar, count in avatar_counts.items():
        bar = "█" * int(count/N*20)
        print(f"    {avatar:<30} {count:>4}  {pct(count,N):>5}  {bar}")

    print("\n  Mean dimension scores (out of 10):")
    dims = ["sweet","salty","sour","umami","crunchy","adventurous"]
    for d in dims:
        mean = profiles_df[d].mean()
        bar  = "█" * int(mean*2)
        print(f"    {d.capitalize():<15} {mean:>4.1f}  {bar}")

    # ── Neophobia Index ───────────────────────────────────────────────────────
    print_section("FOOD NEOPHOBIA INDEX")
    # Lower score = more neophobic (avoids new food)
    neophobia_q = {
        "q9_new":       {"Yes, definitely!":3,"Maybe once or twice":2,"Not really":1,"No":0},
        "q10_new_food": {"Try it straight away!":3,"Ask what it is first":2,
                          "Depends how it looks":1,"I usually avoid it":0},
        "q20_substitute":{"Definitely yes!":2,"Maybe, if it tastes similar":1,
                           "Not sure":0,"Probably not":0},
    }
    def neophobia_score(row):
        score = 0
        for col, mp in neophobia_q.items():
            score += mp.get(row.get(col,""), 0)
        return score  # 0–8: 0-2 Neophobic, 3-5 Moderate, 6-8 Adventurous

    df["neophobia_score"] = df.apply(neophobia_score, axis=1)
    neo_bins = pd.cut(df["neophobia_score"], bins=[-1,2,5,8], labels=["Neophobic (0–2)","Moderate (3–5)","Adventurous (6–8)"])
    neo_counts = neo_bins.value_counts().sort_index()
    for label, count in neo_counts.items():
        bar = "█" * int(count/N*20)
        print(f"    {str(label):<25} {count:>4}  {pct(count,N):>5}  {bar}")
    print(f"\n  Mean neophobia score: {df['neophobia_score'].mean():.2f} / 8")
    print(f"  (Higher = more adventurous, Lower = more neophobic)")

    # ── Optional: Email export ─────────────────────────────────────────────────
    if args.export_emails:
        print_section("EMAIL LIST (for report mailout)")
        emails = df[df["email"].notna() & (df["email"].str.strip() != "")]["email"].tolist()
        for e in emails:
            print(f"    {e}")
        print(f"\n  Total: {len(emails)} emails")

    # ── FILE EXPORTS ──────────────────────────────────────────────────────────
    out = args.output_dir.rstrip("/")

    # 1. Raw CSV
    csv_path = f"{out}/responses.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n✅ responses.csv saved → {csv_path}  ({N} rows)")

    # 2. Summary JSON
    summary = {
        "generated_at": datetime.now().isoformat(),
        "total_responses": N,
        "date_range": {"from": str(df["submitted_at"].min().date()),
                       "to":   str(df["submitted_at"].max().date())},
        "by_level": df["q2_level"].value_counts().to_dict(),
        "by_gender": df["q3_gender"].value_counts().to_dict(),
        "top_flavour": df["q5_flavour"].value_counts().head(3).to_dict(),
        "top_texture": df["q4_texture"].value_counts().head(3).to_dict(),
        "top_snack":   df["q6_snack"].value_counts().head(3).to_dict(),
        "avatar_distribution": profiles_df["avatar_name"].value_counts().to_dict(),
        "mean_dimensions": {d: round(profiles_df[d].mean(), 2) for d in dims},
        "neophobia": {
            "mean_score": round(df["neophobia_score"].mean(), 2),
            "distribution": neo_counts.to_dict()
        },
        "emails_collected": int(len(emails_with_data)),
        "open_to_substitution_pct": int(
            df["q20_substitute"].isin(["Definitely yes!","Maybe, if it tastes similar"]).sum() / N * 100
        ),
    }
    json_path = f"{out}/summary.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"✅ summary.json saved  → {json_path}")

    # 3. Flavour profiles CSV
    profiles_df["id"] = df["id"].values
    profiles_df["q2_level"] = df["q2_level"].values
    profiles_df["submitted_at"] = df["submitted_at"].values
    fp_path = f"{out}/flavour_profiles.csv"
    profiles_df.to_csv(fp_path, index=False)
    print(f"✅ flavour_profiles.csv → {fp_path}")

    print_header("Analysis complete 🌱")
    print(f"  Files written to: {out}/")
    print(f"  Run with --export-emails to list emails for report mailout")
    print(f"  Run with --level P3 to filter by school level")


if __name__ == "__main__":
    main()
