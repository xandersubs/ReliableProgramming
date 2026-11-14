"""SQLite persistence. Contains deliberate reliability/security problems."""
import sqlite3
from models import Product


class StoreRepository:
    def __init__(self, db_path='shop.db'):
        self.db_path = db_path

    def connect(self):
        return sqlite3.connect(self.db_path, timeout=2)

    def get_product(self, sku):
        conn = self.connect()
        row = conn.execute('SELECT sku, name, price, stock FROM products WHERE sku = ?', (sku,)).fetchone() 
        #The SKU was pasted into the SQL with an f-string which could allow for SQL injections by the user changing the query and returning a product the caller never asked for now the value is sent separately from the SQL so it can only ever be treated as data
        conn.close()
        return Product(*row) if row else None

    def get_saved_cart(self, user_id):
        conn = self.connect()
        rows = conn.execute('SELECT sku, quantity FROM saved_cart WHERE user_id = ?', (user_id,)).fetchall() 
        # user_id was pasted into the SQL with an f-string allowing SQL injection that could expose every user's saved cart Now uses a ? placeholder so it is treated only as data
        conn.close()
        return rows

    def save_cart(self, user_id, lines):
        conn = self.connect()
        conn.execute('DELETE FROM saved_cart WHERE user_id = ?', (user_id,))
        for line in lines:
            conn.execute('INSERT INTO saved_cart VALUES (?, ?, ?)', (user_id, line.sku, line.quantity))
        conn.commit()
        conn.close()

    def update_stock(self, sku, quantity):
        conn = self.connect()
        cur = conn.execute('UPDATE products SET stock = stock - ? WHERE sku = ? AND stock >= ?', (quantity, sku, quantity)) 
        #Before there was no check so the store could oversell callers of the function also had no way to know whether the update worked which is why the return of rowcount was added to signify a change aswell as adding AND stock >= ? to the where along with what was mentioned before means that when there isnt enough stock nothing changes and the function returns false the check and the subtraction also happen in one SQL statement so another checkout cant slip in between them
        conn.commit()
        conn.close()
        return cur.rowcount == 1


    def save_order(self, user_id, amount, status, request_id):
        conn = self.connect()
        cur = conn.execute('INSERT INTO orders(user_id, amount, status, request_id) VALUES (?, ?, ?, ?)',
                           (user_id, amount, status, request_id))
        conn.commit()
        order_id = cur.lastrowid
        conn.close()
        return order_id

    def list_orders(self, user_id):
        conn = self.connect()
        rows = conn.execute('SELECT id, user_id, amount, status FROM orders  WHERE user_id = ? ORDER BY id DESC', (user_id,)).fetchall() 
        #Originally the function took a user_id but never used it so any user could see all the orders which leads to a privacy leak now filters with WHERE user_id = ? so users only see their own orders
        conn.close()
        return rows

    def get_order_by_request_id(self, request_id): 
        conn = self.connect()
        row = conn.execute('SELECT id, status, amount FROM orders WHERE request_id = ?', (request_id,)).fetchone()
        conn.close()
        return row
    #These changes to the above lines along with the changes made in checkout.py and setup_db.py prevent the previous error where a retry or a double-click with the same request_id charged the card again and took the stock again the old amount > 1000 block only printed messages and did nothing now checkout() looks up the request_id first and returns the existing order if there is one and request_id TEXT UNIQUE in the schema is in place to ensure the database itself rejects duplicate orders also lets checkout look up an existing order by request_id, so a repeated request returns the original order instead of charging again.
