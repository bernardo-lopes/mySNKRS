"""
Local SQLite Storage for Sneaker Valuations and User Inventory / Closet.
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import ValuationReport


WORKSPACE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = Path(os.getenv("SNKRS_DB_PATH", str(WORKSPACE_DIR / "snkrs_data.db")))


class SneakerStorage:
    """Manages saved sneaker estimations and portfolio."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sku TEXT NOT NULL,
                    model_name TEXT,
                    size_input TEXT,
                    condition TEXT,
                    box_condition TEXT,
                    fair_market_price REAL,
                    quick_sale_price REAL,
                    patient_sale_price REAL,
                    stockx_reference REAL,
                    best_platform TEXT,
                    currency TEXT,
                    full_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sku TEXT NOT NULL,
                    model_name TEXT,
                    size TEXT,
                    condition TEXT,
                    box_condition TEXT,
                    purchase_price REAL DEFAULT 0.0,
                    target_price REAL,
                    status TEXT DEFAULT 'for_sale', -- for_sale, sold
                    sold_price REAL,
                    sold_platform TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # StockX data synced from your own browser (see stockx_sync.py)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stockx_products (
                    sku TEXT PRIMARY KEY,
                    title TEXT,
                    url TEXT,
                    image_url TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stockx_market (
                    sku TEXT NOT NULL,
                    size_key TEXT NOT NULL,
                    size_label TEXT,
                    highest_bid REAL,
                    lowest_ask REAL,
                    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (sku, size_key)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stockx_sales (
                    sku TEXT NOT NULL,
                    size_key TEXT NOT NULL,
                    size_label TEXT,
                    sold_at TEXT NOT NULL,
                    price REAL NOT NULL,
                    UNIQUE (sku, size_key, sold_at, price)
                )
            """)
            # Columns added after the first release
            inventory_cols = {r[1] for r in conn.execute("PRAGMA table_info(inventory)")}
            if "favorite" not in inventory_cols:
                conn.execute("ALTER TABLE inventory ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0")
            product_cols = {r[1] for r in conn.execute("PRAGMA table_info(stockx_products)")}
            if "retail_price" not in product_cols:
                conn.execute("ALTER TABLE stockx_products ADD COLUMN retail_price REAL")
            if "model" not in product_cols:
                conn.execute("ALTER TABLE stockx_products ADD COLUMN model TEXT")
            conn.commit()

    def save_evaluation(self, report: ValuationReport) -> int:
        """Saves an evaluation report to history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO evaluations (
                    sku, model_name, size_input, condition, box_condition,
                    fair_market_price, quick_sale_price, patient_sale_price,
                    stockx_reference, best_platform, currency, full_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.sku,
                report.model_name,
                report.size_input,
                report.condition.value,
                report.box_condition.value,
                report.fair_market_price,
                report.quick_sale_price,
                report.patient_sale_price,
                report.stockx_reference_price,
                report.best_platform_to_sell,
                report.currency,
                report.model_dump_json()
            ))
            conn.commit()
            return cursor.lastrowid

    def get_recent_evaluations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent valuations."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, sku, model_name, size_input, condition, box_condition,
                       fair_market_price, stockx_reference, best_platform, currency, created_at
                FROM evaluations
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def add_to_inventory(
        self,
        sku: str,
        model_name: str,
        size: str,
        condition: str,
        box_condition: str,
        purchase_price: Optional[float] = None,
        target_price: Optional[float] = None,
        notes: str = ""
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inventory (
                    sku, model_name, size, condition, box_condition,
                    purchase_price, target_price, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (sku.strip().upper(), model_name, size, condition, box_condition, purchase_price, target_price, notes))
            conn.commit()
            return cursor.lastrowid

    def get_inventory(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT * FROM inventory WHERE status = ? ORDER BY created_at DESC, id DESC", (status,))
            else:
                cursor.execute("SELECT * FROM inventory ORDER BY created_at DESC, id DESC")
            return [dict(row) for row in cursor.fetchall()]

    INVENTORY_EDITABLE = (
        "sku", "model_name", "size", "condition", "box_condition",
        "purchase_price", "target_price", "status", "sold_price", "sold_platform", "notes", "favorite",
    )

    def update_inventory_item(self, item_id: int, fields: Dict[str, Any]) -> bool:
        fields = {k: v for k, v in fields.items() if k in self.INVENTORY_EDITABLE}
        if "sku" in fields and fields["sku"]:
            fields["sku"] = fields["sku"].strip().upper()
        if not fields:
            return False
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                f"UPDATE inventory SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?",
                (*fields.values(), item_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def delete_inventory_item(self, item_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
            conn.commit()
            return cur.rowcount > 0

    def save_stockx_sync(
        self,
        sku: str,
        title: Optional[str],
        url: Optional[str],
        image_url: Optional[str],
        market: Optional[Dict[str, Any]],
        sales: List[Dict[str, Any]],
        retail_price: Optional[float] = None,
        model: Optional[str] = None,
    ) -> int:
        """Stores a StockX sync. Sales are merged (deduplicated), so history accumulates across syncs.
        Returns the number of new sales added."""
        sku = sku.strip().upper()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO stockx_products (sku, title, url, image_url, retail_price, model, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(sku) DO UPDATE SET
                    title = COALESCE(excluded.title, title),
                    url = COALESCE(excluded.url, url),
                    image_url = COALESCE(excluded.image_url, image_url),
                    retail_price = COALESCE(excluded.retail_price, retail_price),
                    model = COALESCE(excluded.model, model),
                    updated_at = CURRENT_TIMESTAMP
            """, (sku, title, url, image_url, retail_price, model))
            if market:
                conn.execute("""
                    INSERT OR REPLACE INTO stockx_market (sku, size_key, size_label, highest_bid, lowest_ask, synced_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (sku, market["size_key"], market["size_label"], market["highest_bid"], market["lowest_ask"]))
            before = conn.total_changes
            conn.executemany("""
                INSERT OR IGNORE INTO stockx_sales (sku, size_key, size_label, sold_at, price)
                VALUES (?, ?, ?, ?, ?)
            """, [(sku, s["size_key"], s["size"], s["sold_at"], s["price"]) for s in sales])
            added = conn.total_changes - before
            conn.commit()
            return added

    def get_stockx_product(self, sku: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM stockx_products WHERE sku = ?", (sku.strip().upper(),)).fetchone()
            return dict(row) if row else None

    def get_stockx_market(self, sku: str, size_key: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM stockx_market WHERE sku = ? AND size_key = ?", (sku.strip().upper(), size_key)
            ).fetchone()
            return dict(row) if row else None

    def get_stockx_sales(self, sku: str, size_key: str) -> List[Dict[str, Any]]:
        """All stored sales for a SKU and size, newest first, as {"date", "price", "size"}."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT sold_at, price, size_label FROM stockx_sales
                WHERE sku = ? AND size_key = ? ORDER BY sold_at DESC
            """, (sku.strip().upper(), size_key)).fetchall()
            return [{"date": r[0], "price": r[1], "size": r[2]} for r in rows]

    def get_stockx_size_keys(self, sku: str) -> List[str]:
        """Sizes that have any synced StockX data for this SKU."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT size_key FROM stockx_market WHERE sku = ?
                UNION SELECT DISTINCT size_key FROM stockx_sales WHERE sku = ?
            """, (sku.strip().upper(), sku.strip().upper())).fetchall()
            return [r[0] for r in rows]
