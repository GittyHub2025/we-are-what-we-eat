# 🌱 We Are What We Eat — Isaac's Food Explorer Survey

> A longitudinal research project studying children's food preferences and eating habits from Primary 3 to Primary 6 in Singapore.
> Started by **Isaac**, age 9 · Supported by family, teachers & the community · 2026

---

## 🎯 About This Project

This project explores how children's food preferences are formed, and how **flavour profiling** can help guide children toward healthier food choices — not through moralising, but through **substitution via similarity** (finding healthier alternatives that match a child's existing taste preferences).

**Research pillars:**
- 🔬 **Scientific / Psychological** — Understanding Food Neophobia and flavour preference formation
- 📊 **Data / Analytical** — Longitudinal behavioural tracking (P3 → P6)
- 🎮 **Gamification / Entrepreneurial** — Food Avatars based on individual flavour profiles

---

## 🚀 Setup Guide

### Step 1 — Fork or Clone This Repo

```bash
git clone https://github.com/GittyHub2025/we-are-what-we-eat.git
cd we-are-what-we-eat
```

### Step 2 — Create a Private Data Repository

To store survey responses, create a **separate private GitHub repository** called `we-are-what-we-eat-data`.

> ⚠️ Keep this private — it will contain email addresses (PDPA compliance)

### Step 3 — Create a GitHub Personal Access Token (PAT)

1. Go to: **https://github.com/settings/tokens**
2. Click **"Generate new token (classic)"**
3. Give it a name: `we-are-what-we-eat-survey`
4. Select scope: ✅ **`repo`** (full repo access — needed for private repos)
5. Click **Generate token** and **copy it immediately** (you won't see it again)

### Step 4 — Configure `index.html`

Open `index.html` and find the `CONFIG` block near the bottom:

```javascript
const CONFIG = {
  GITHUB_TOKEN: 'YOUR_GITHUB_PAT_HERE',       // ← Paste your PAT here
  GITHUB_OWNER: 'YOUR_GITHUB_USERNAME',        // ← Your GitHub username
  GITHUB_REPO:  'we-are-what-we-eat-data',     // ← Your private data repo
  ENABLED: false   // ← Change to: true
};
```

Replace the placeholder values and set `ENABLED: true`.

### Step 5 — Enable GitHub Pages

1. Go to your survey repo → **Settings** → **Pages**
2. Under **Source**, select `Deploy from a branch`
3. Choose `main` branch → `/ (root)` → **Save**
4. Your survey will be live at: `https://GittyHub2025.github.io/we-are-what-we-eat/`

---

## 📦 Repository Structure

```
we-are-what-we-eat/
├── index.html          ← The survey form (deploy this via GitHub Pages)
├── README.md           ← This file
└── .github/
    └── ISSUE_TEMPLATE/
        └── survey_response.md   ← Issue template (optional)

we-are-what-we-eat-data/   ← SEPARATE private repo
└── (GitHub Issues = one issue per survey response)
```

---

## 🗄️ How Data is Stored

Each survey submission creates a **GitHub Issue** in the private data repository:

- **Issue title:** `Survey Response · 2026-02-19 · P3 · FOOD-1A2B3C`
- **Issue body:** Structured markdown table with all 25 question responses
- **Labels:** `survey-response`, `P3` (school level), etc.

**Viewing responses:**
- Go to your private `we-are-what-we-eat-data` repo → **Issues**
- Filter by label (e.g. `P3`) to see responses from a specific school level
- Export via GitHub API: `GET /repos/{owner}/{repo}/issues?labels=survey-response`

---

## 🎨 Brand Color Palette

| Swatch | Name | Hex | Usage |
|--------|------|-----|-------|
| 🍊 | **Tangerine Fire** | `#FF6B35` | Primary brand, CTAs, energy |
| 🌿 | **Fresh Leaf** | `#52B788` | Health, growth, nature |
| 🌟 | **Sunshine** | `#FFD93D` | Joy, milestones, highlights |
| 💜 | **Berry Burst** | `#9B5DE5` | Discovery, creativity, accents |
| 🩵 | **Ocean Splash** | `#00BBF9` | Trust, exploration, info |
| 🌸 | **Blossom** | `#FF85A1` | Warmth, approachability |
| 🤍 | **Cloud** | `#FFF8F0` | Card backgrounds, clarity |
| 🖤 | **Midnight** | `#2C2C2C` | Body text, high contrast |

**Background gradient:** `160deg · #FF6B35 → #F7931E → #FFD93D → #52B788 → #00BBF9 → #9B5DE5`

---

## 📊 Survey Structure

| Section | Questions | Theme |
|---------|-----------|-------|
| 0 · Consent | PDPA | Parent consent & data notice |
| 1 · About You | Q1–3 | Demographic warm-up |
| 2 · Flavour DNA | Q4–10 | Taste & texture preferences |
| ⭐ Milestone 1 | — | Fun fact: seaweed & taste buds |
| 3 · Food Life | Q11–17 | Behavioural eating habits |
| ⭐ Milestone 2 | — | Fun fact: gut microbiome |
| 4 · Food Explorer | Q18–22 | Cultural exposure & openness |
| ⭐ Milestone 3 | — | Parent tip: flavour bridging |
| 5 · Health Awareness | Q23–25 | Self-awareness & goals |
| 6 · Email Capture | Optional | Personalised report opt-in |

---

## 🔒 PDPA Compliance Notes

- No full names collected
- Email is explicitly optional
- Data stored in a **private** GitHub repository
- Consent checkbox required before form can be submitted
- Participants may request data deletion by contacting the project owner
- Data used only for educational research purposes

---

## 🗺️ Project Roadmap

- [x] **Phase 1** — Survey form + GitHub storage (current)
- [ ] **Phase 2** — Automated analysis report generation
- [ ] **Phase 3** — Food Avatar creation (gamification layer)
- [ ] **Phase 4** — Year 2 follow-up survey (P4 cohort)
- [ ] **Phase 5** — Longitudinal data comparison (P3 → P6)

---

## 📬 Contact

Project lead: **Isaac** (P3, Singapore, 2026)
For questions or to request data deletion: _(add contact email here)_

---

*🌱 We are what we eat — and understanding that is the first step to eating better.*
