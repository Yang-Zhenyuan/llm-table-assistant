# -*- coding: utf-8 -*-
"""
Created on Sat Aug 15 17:33:55 2025

@author: LENOVO
"""

import os
import requests
import sqlite3
import pandas as pd

def download_file(url, filename):
    if not os.path.exists(filename):
        print(f"Downloading {filename} ...")
        r = requests.get(url)
        r.raise_for_status()
        with open(filename, "wb") as f:
            f.write(r.content)
        print(f"Downloaded {filename}")

def export_all_tables(db_path, prefix):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"[{prefix}] Found {len(tables)} tables: {tables}")
    for table in tables:
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        df.to_csv(f"data/{prefix}_{table}.csv", index=False)
        print(f"Exported data/{prefix}_{table}.csv")
    conn.close()

# Sakila (SQLite version)
sakila_url = "https://github.com/bradleygrant/sakila-sqlite3/raw/main/sakila_master.db"
download_file(sakila_url, "Sakila.db")
export_all_tables("Sakila.db", "Sakila")
