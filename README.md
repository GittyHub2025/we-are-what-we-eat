# 🌱 We Are What We Eat — Isaac's Food Explorer Survey

> A longitudinal research project studying children's food preferences and eating habits from Primary 3 to Primary 6 in Singapore.
> Started by **Isaac**, age 9 · Supported by family, teachers & the community · 2026

**🌐 Live Survey:** https://GittyHub2025.github.io/we-are-what-we-eat/

---

## 🎯 About This Project

This project explores how children's food preferences are formed, and how **flavour profiling** can help guide children toward healthier food choices — not through moralising, but through **substitution via similarity** (finding healthier alternatives that match a child's existing taste preferences).

**Research pillars:**
- 🔬 **Scientific / Psychological** — Understanding Food Neophobia and flavour preference formation
- 📊 **Data / Analytical** — Longitudinal behavioural tracking (P3 → P6)
- 🎮 **Gamification / Entrepreneurial** — Food Avatars based on individual flavour profiles

---

## 🏗️ Architecture

```
Survey form (GitHub Pages)
    └── Supabase (PostgreSQL)  ← responses stored here
          └── analyse.py       ← Python script to analyse & export
```

- **Form** hosted on GitHub Pages — public, no server needed
- **Database** on Supabase (free tier, Singapore region) — secure PostgreSQL
- **Anon key** is safe to embed in client-side code by design (Row Level Security enforces INSERT-only for public users; only the project owner can read or delete)

---

## 📦 Repository Structure

```
we-are-what-we-eat/
├── index.html      ← Survey form (live on GitHub Pages)
├── analyse.py      ← Python analysis & export script
└── README.md       ← This file
```

---

## 📊 Survey Structure (25 Questions)

| Section | Questions | Theme |
|---------|-----------|-------|
| Consent | — | PDPA parent consent |
| 1 · About You | Q1–3 | Demographics |
| 2 · Flavour DNA | Q4–10 | Taste & texture preferences |
| ⭐ Milestone 1 | — | Fun fact: seaweed & taste buds |
| 3 · Food Life | Q11–17 | Behavioural eating habits |
| ⭐ Milestone 2 | — | Fun fact: gut microbiome |
| 4 · Food Explorer | Q18–22 | Cultural exposure & openness |
| ⭐ Milestone 3 | — | Parent tip: flavour bridging |
| 5 · Health Awareness | Q23–25 | Self-awareness & goals |
| Email | Optional | Personalised report opt-in |

---

## 🗄️ Database Schema (Supabase)

```sql
CREATE TABLE survey_responses (
  id            uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  submitted_at  timestamptz DEFAULT now(),
  q1_who        text,  q2_level text,  q3_gender text,
  q4_texture    text,  q5_flavour text, q6_snack text,
  q7_spicy      text,  q8_fruit text,  q9_new text,  q10_new_food text,
  q11_veg       text,  q12_drinks text, q13_fried text,
  q14_family    text,  q15_snack_decide text, q16_breakfast text, q17_school text,
  q18_cuisine   text[],  q19_adv text[],
  q20_substitute text, q21_intro text, q22_convo text,
  q23_feel      text,  q24_healthy text[], q25_improve text,
  email         text
);

-- Row Level Security: public can INSERT only; owner can read all
ALTER TABLE survey_responses ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public inserts" ON survey_responses FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Allow owner to read all" ON survey_responses FOR SELECT TO authenticated USING (true);
```

---

## 🐍 Running the Analysis Script

```bash
# Install dependencies
pip install supabase pandas tabulate

# Full analysis + export files
python analyse.py

# Filter by school level
python analyse.py --level P3

# Only responses after a date
python analyse.py --since 2026-03-01

# Export email list for report mailout
python analyse.py --export-emails

# Save output files to a specific folder
python analyse.py --output-dir ./results
```

**Output files:**
- `responses.csv` — flat export of every single response (for Excel, SPSS, etc.)
- `summary.json` — aggregated counts for every question (for dashboards)
- `flavour_profiles.csv` — per-respondent Flavour Avatar scores across 6 dimensions

**6 Flavour Dimensions scored per respondent:**
- 🍭 Sweet · 🧂 Salty · 🍋 Sour · 🍜 Umami · 🥨 Crunchy · 🌍 Adventurous

**6 Food Avatars assigned by dominant dimension:**
- 🍭 Sweet Seeker · 🧂 Salt Captain · 🍋 Sour Sparks · 🍜 Umami Master · 🥨 Crunch Hero · 🌍 Food Explorer

---

## 🎨 Brand Color Palette

| | Name | Hex | Usage |
|---|---|---|---|
| 🍊 | **Tangerine Fire** | `#FF6B35` | Primary brand, CTAs, energy |
| 🌿 | **Fresh Leaf** | `#52B788` | Health, growth, nature |
| 🌟 | **Sunshine** | `#FFD93D` | Joy, milestones, highlights |
| 💜 | **Berry Burst** | `#9B5DE5` | Discovery, creativity |
| 🩵 | **Ocean Splash** | `#00BBF9` | Trust, exploration |
| 🌸 | **Blossom** | `#FF85A1` | Warmth, approachability |
| 🤍 | **Cloud** | `#FFF8F0` | Card backgrounds |
| 🖤 | **Midnight** | `#2C2C2C` | Body text |

---

## 🗺️ Project Roadmap

- [x] **Phase 1** — Survey form on GitHub Pages + Supabase storage ✅
- [x] **Phase 1b** — Python analysis script (flavour profiles, neophobia index) ✅
- [ ] **Phase 2** — Automated personalised Food Avatar Report (PDF per respondent)
- [ ] **Phase 3** — Interactive dashboard (Streamlit or Looker Studio)
- [ ] **Phase 4** — Year 2 follow-up survey (P4 cohort)
- [ ] **Phase 5** — Longitudinal comparison (P3 → P6)

---

## 🔒 PDPA Compliance

- No full names collected at any point
- Email is explicitly optional with clear purpose stated
- Data stored in project owner's Supabase account (Singapore-proximate region)
- Public users can only INSERT — they cannot read other responses
- Participants may request data deletion by contacting the project owner
- Data used only for educational research purposes

---

*🌱 We are what we eat — and understanding that is the first step to eating better.*
