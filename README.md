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

# Assumptions
1. A request_id identifies one checkout attempt repeating it returns the original result even if that was a decline to actually retry the client sends a new ID
2. Only one coupon can be active at a time and the newest one replaces the previous one but FREESHIP doesnt change the total becuase the model has no shipping cost 
3. load() replaces the in memory cart rather than merging with it 
4. failed payments still save an order row as an audit trail
5. a total discounted to $0 still goes through the simulated gateway 
6. two checkouts with the same request_id running at exactly the same moment could both get past the lookup but UNIQUE sotps the second order row from being saved but not the second charge 