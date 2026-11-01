# 👟 SNKRS — Sneaker Market Price Valuation & Reselling Intelligence

A specialized market intelligence and price estimation platform for sneakerheads and resellers.  
Provide your sneaker's **Model Reference (SKU)**, **Size**, and **Condition** to receive an instant, multi-platform valuation, market consensus pricing, and net profit optimization after seller fees.

---

## 🎯 Marketplaces Covered

1. **StockX** *(Primary Market Reference / Benchmark)*:
   - The gold standard for **Deadstock (Brand New in Box)** baseline pricing.
   - Tracks **Lowest Ask**, **Highest Bid** (instant cash-out), **Last Sale Price**, and retail price.
2. **GOAT** *(Recommended Sneaker Platform)*:
   - The #1 global alternative to StockX.
   - Natively supports both **Deadstock** and **Used / Pre-Owned** sneakers with box condition grading (Damaged Box, Missing Lid, No Box).
3. **eBay** *(Real-World Clearinghouse)*:
   - Analyzes both active Buy-It-Now listings and **Sold / Completed transactions** (revealing what buyers actually pay, filtering out dreamer asking prices).
   - Accounts for the Authenticity Guarantee program.
4. **Vinted** *(Max Profit / 0% Seller Fees)*:
   - Major peer-to-peer marketplace where **sellers pay 0% commission** (the buyer pays buyer protection and shipping!).
   - Ideal for used pairs, beaters, or maximizing net take-home cash.

---

## 🧠 Valuation Algorithm & Depreciation Model

Sneaker prices do not depreciate linearly. Our valuation engine utilizes real-world secondary market resale curves:

### 1. Condition Multiplier
- **Deadstock (DS - 10/10)**: `1.00x` (100% of StockX DS baseline)
- **VNDS / PADS (9.5/10)**: `0.91x` (Tried on indoors / worn once)
- **Used - Like New (9/10)**: `0.82x` (Minimal creasing, clean uppers, zero sole wear)
- **Used - Good (7.5 - 8.5/10)**: `0.70x` (Standard pre-owned, minor star loss)
- **Used - Fair (5 - 7/10)**: `0.52x` (Visible creasing, midsole scuffs, heel wear)
- **Beat / Restoration (<5/10)**: `0.35x` (Beaters, project pairs, heavy separation)

### 2. Box & Packaging Penalty
- **Original Box (Good Condition)**: `1.00x`
- **Original Box (Damaged / Missing Lid)**: `0.94x` (-6%)
- **Replacement Box**: `0.88x` (-12%)
- **No Box (Shoes Only)**: `0.80x` (-20% value penalty; automatically flags that StockX rejects the pair)

### 3. Net Cash in Pocket Calculator (After Fees)
The platform compares what you **actually take home in cash** after platform deductions:
- **StockX**: 9.0% commission + 3.0% payment processing = **12.0% fee**
- **GOAT**: 9.5% commission + 2.9% cash out + $5.00 fixed fee = **~12.4% + €4.50**
- **eBay**: **8.0%** (for Authenticity Guarantee shoes >= €150) or **13.25% + €0.35** (< €150)
- **Vinted**: **0.0% seller fee** — you keep 100% of your sale price!

---

## 🚀 Quickstart & Usage

### 1. Setup Virtual Environment
```bash
python3.12 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### 2. Run the Web Dashboard
Launch the modern sneakerhead dashboard:
```bash
PYTHONPATH=. ./venv/bin/python -m snkrs.cli web --port 8000
```
Open **`http://127.0.0.1:8000`** in your browser.

Features included in the Web UI:
- Interactive SKU lookup with auto-suggested popular drops (Panda Dunks, Lost & Found, Travis Scott, Samba OG, etc.).
- Multi-format size converter (US Men, US Women, EU, UK, CM).
- Visual Condition & Box condition selectors.
- Pricing cards: **Quick Flip (24-48h)**, **Fair Market Target**, and **Top Dollar (Patient)**.
- Full platform comparison table showing exact Net Take-Home cash.
- Actionable reseller cleaning and listing tips.

---

### 3. Command Line Interface (CLI)

#### Instant Valuation:
```bash
# Evaluate by SKU, Size, Condition, and Box
PYTHONPATH=. ./venv/bin/python -m snkrs.cli estimate \
  --sku DD1391-100 \
  --size "EU 44" \
  --condition used_good \
  --box original_good
```

#### Interactive Mode:
Simply run:
```bash
PYTHONPATH=. ./venv/bin/python -m snkrs.cli estimate
```
The CLI will interactively prompt you for SKU, Size, and Condition.

#### Popular Reference Drops:
```bash
PYTHONPATH=. ./venv/bin/python -m snkrs.cli popular
```

#### View Valuation History:
```bash
PYTHONPATH=. ./venv/bin/python -m snkrs.cli history
```

---

## 🧪 Testing

Run the automated test suite with:
```bash
PYTHONPATH=. ./venv/bin/pytest tests/ -v
```

---

## 📁 Project Architecture

```
snkrs/
├── snkrs/
│   ├── models.py             # Pydantic schemas (ConditionGrade, BoxCondition, ValuationReport)
│   ├── size_converter.py      # US/EU/UK/CM size normalization engine
│   ├── valuation.py          # Market consensus & fee net profit calculator
│   ├── storage.py            # SQLite local persistence for valuation history & closet inventory
│   ├── cli.py                # Rich terminal UI
│   ├── platforms/
│   │   ├── base.py           # Abstract marketplace class
│   │   ├── stockx.py         # StockX benchmark reference client
│   │   ├── goat.py           # GOAT new & used sneakers connector
│   │   ├── ebay.py           # eBay sold & active listings connector
│   │   ├── vinted.py         # Vinted catalog connector (0% fee calculator)
│   │   └── aggregator.py     # Concurrent multi-platform orchestrator
│   └── web/
│       ├── app.py            # FastAPI application
│       └── templates/
│           └── index.html    # Tailwind CSS interactive dashboard
├── tests/
│   ├── test_size_converter.py
│   ├── test_valuation.py
│   └── test_web.py
├── requirements.txt
└── README.md
```
