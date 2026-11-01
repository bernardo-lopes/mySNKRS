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
        purchase_price: float,
        target_price: float,
        notes: str = ""
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inventory (
                    sku, model_name, size, condition, box_condition,
                    purchase_price, target_price, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (sku, model_name, size, condition, box_condition, purchase_price, target_price, notes))
            conn.commit()
            return cursor.lastrowid

    def get_inventory(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inventory ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
