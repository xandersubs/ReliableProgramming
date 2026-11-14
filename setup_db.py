"""Initialize demo data in a chosen local SQLite file."""
import sqlite3
import sys

SCHEMA = '''
CREATE TABLE IF NOT EXISTS products (sku TEXT PRIMARY KEY, name TEXT NOT NULL, price REAL NOT NULL, stock INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS saved_cart (user_id TEXT NOT NULL, sku TEXT NOT NULL, quantity INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, amount REAL, status TEXT, request_id TEXT UNIQUE);
'''
# These changes to the above lines along with the changes made in repository.py and checkout.py prevent the previous error where a retry or a double-click with the same request_id charged the card again and took the stock again the old amount > 1000 block only printed messages and did nothing now checkout() looks up the request_id first and returns the existing order if there is one and request_id TEXT UNIQUE in the schema is in place to ensure the database itself rejects duplicate orders

def initialize(db_path='shop.db'):
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.executemany('INSERT OR IGNORE INTO products VALUES (?, ?, ?, ?)', [
            ('LAP-01', 'Laptop', 999.99, 5),
            ('MOU-01', 'Wireless mouse', 29.95, 20),
            ('USB-01', 'USB cable', 9.99, 50),
        ])


if __name__ == '__main__':
    initialize(sys.argv[1] if len(sys.argv) > 1 else 'shop.db')
