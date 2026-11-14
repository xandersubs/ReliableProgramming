# Order-processing system — student starter

This application intentionally contains defects. Your assignment has three parts only:

1. Identify and correct at least 8 meaningful defects.
2. Write at least 12 automated unit tests with `pytest`.
3. Add `.github/workflows/tests.yml` to run tests on pushes and pull requests.

## Application files

- `models.py`: domain objects
- `cart.py`: shopping cart and discounts
- `repository.py`: SQLite products, saved carts, inventory and orders
- `checkout.py`: checkout workflow
- `payments.py`: simulated payment gateway
- `setup_db.py` and `demo.py`: demo database and execution
- `tests/test_smoke.py`: minimal smoke tests (not a solution)

## Running locally

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python setup_db.py
python demo.py
```

Use temporary databases and fake payment tokens for unit tests. No real payment credentials are required.

# Defects fixed

Each fix is explained in a comment beside the change. Tests are in `tests/test_fixes.py`.

| # | File | Defect | Fix | Test |
|---|------|--------|-----|------|
| 1 | `cart.py` | `add_item` accepted 0 or negative quantities (negative charge) | Reject `quantity <= 0` | `test_add_item_rejects_zero_and_negative` |
| 2 | `cart.py` | Stock check ignored what was already in the cart (15 + 10 mice with 20 in stock) | Check `already + quantity` against stock | `test_add_item_counts_what_is_already_in_cart` |
| 3 | `cart.py` | `remove_item` with a negative quantity added items | Reject negative quantities | `test_remove_item_rejects_negative` |
| 4 | `cart.py` | Discount amount was frozen, so later cart edits were ignored | Store only the code; `total()` recalculates from current subtotal | `test_discount_updates_when_cart_changes` |
| 5 | `cart.py` | Discount codes stacked | New code replaces the old one | `test_discounts_do_not_stack` |
| 6 | `cart.py` | Total could go negative (SAVE15 on $9.99 gave -$5.01) | `round(max(amount, 0), 2)` | `test_total_never_negative` |
| 7 | `cart.py` | `load()` twice duplicated items (3 became 9) | Reset `self.lines` before loading | `test_load_twice_does_not_duplicate` |
| 8 | `repository.py` | SQL injection in `get_product` (f-string) | `?` placeholder | `test_get_product_blocks_sql_injection` |
| 9 | `repository.py` | SQL injection in `get_saved_cart` (f-string) | `?` placeholder | `test_get_saved_cart_blocks_sql_injection` |
| 10 | `repository.py` | `list_orders` ignored `user_id` and returned everyone's orders | `WHERE user_id = ?` | `test_list_orders_only_shows_own_orders` |
| 11 | `repository.py` | `update_stock` let stock go negative and reported nothing | `AND stock >= ?` in one atomic statement; return `rowcount == 1` | `test_update_stock_never_negative` |
| 12 | `checkout.py`, `repository.py`, `setup_db.py` | Same `request_id` twice charged the card and took stock twice | Look up existing order by `request_id`; `request_id` is `UNIQUE` in the schema | `test_repeated_checkout_charges_once`, `test_database_blocks_duplicate_request_id` |
| 13 | `checkout.py` | Order was charged even if stock ran out before checkout | Stop and release reserved stock before charging | `test_out_of_stock_does_not_charge` |
| 14 | `checkout.py` | Declined card or gateway crash permanently removed stock | Reserve, charge, then release stock if payment fails | `test_declined_payment_keeps_stock_and_cart`, `test_payment_crash_keeps_stock_and_cart` |
| 15 | `checkout.py` | Failed payment emptied the cart; coupon carried over after a paid order | Clear cart and coupon only after a paid order | `test_paid_checkout_clears_cart_and_coupon`, `test_declined_payment_keeps_stock_and_cart` |
| 16 | `checkout.py` | Payment token was printed to the console (sensitive data leak) | Removed the print | `test_payment_token_not_printed` |

# Assumptions
1. A request_id identifies one checkout attempt repeating it returns the original result even if that was a decline to actually retry the client sends a new ID
2. Only one coupon can be active at a time and the newest one replaces the previous one but FREESHIP doesnt change the total because the model has no shipping cost so that doesnt override other cooupons 
3. load() replaces the in memory cart rather than merging with it 
4. failed payments still save an order row as an audit trail
5. a total discounted to $0 still goes through the simulated gateway 
6. two checkouts with the same request_id running at exactly the same moment could both get past the lookup but UNIQUE stops the second order row from being saved but not the second charge 