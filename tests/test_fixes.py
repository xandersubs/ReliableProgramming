import sqlite3

import pytest

from cart import ShoppingCart
from checkout import CheckoutService
from payments import FakePaymentGateway
from repository import StoreRepository
from setup_db import initialize

def make_cart(tmp_path):
    #Create a fresh test database and an empty cart for user 'alice'.
    db = str(tmp_path / 'test.db')
    initialize(db)
    repo = StoreRepository(db)
    cart = ShoppingCart('alice', repo)
    return repo, cart

class BrokenGateway:
    #Fake payment gateway that crashes, to simulate the payment service being down.
    def charge(self, amount, payment_token):
        raise TimeoutError('gateway down')

# Tests cart.add_item: quantities of 0 or less are rejected (previously accepted)
def test_add_item_rejects_zero_and_negative(tmp_path):
    repo, cart = make_cart(tmp_path)

    assert cart.add_item('USB-01', 0) is False
    assert cart.add_item('USB-01', -1) is False
    assert cart.lines == []

# Tests cart.add_item: stock check includes what's already in the cart
def test_add_item_counts_what_is_already_in_cart(tmp_path):
    repo, cart = make_cart(tmp_path)
    cart.add_item('MOU-01', 15)

    result = cart.add_item('MOU-01', 10)

    assert result is False
    assert cart.lines[0].quantity == 15

# Tests cart.remove_item: negative quantity is rejected
def test_remove_item_rejects_negative(tmp_path):
    repo, cart = make_cart(tmp_path)
    cart.add_item('USB-01', 2)

    result = cart.remove_item('USB-01', -5)

    assert result is False
    assert cart.lines[0].quantity == 2

# Tests cart.total: discount follows cart edits 
def test_discount_updates_when_cart_changes(tmp_path):
    repo, cart = make_cart(tmp_path)
    cart.add_item('MOU-01', 2)
    cart.apply_discount('WELCOME10')

    cart.add_item('MOU-01', 5)

    assert cart.total() == 188.69

# Tests cart.apply_discount: a new code replaces the old one
def test_discounts_do_not_stack(tmp_path):
    repo, cart = make_cart(tmp_path)
    cart.add_item('MOU-01', 2)

    cart.apply_discount('WELCOME10')
    cart.apply_discount('STUDENT20')

    assert cart.total() == 47.92

# Tests cart.total: never below $0 
def test_total_never_negative(tmp_path):
    repo, cart = make_cart(tmp_path)
    cart.add_item('USB-01', 1)

    cart.apply_discount('SAVE15')

    assert cart.total() == 0

# Tests cart.load: loading twice doesn't double the items
def test_load_twice_does_not_duplicate(tmp_path):
    repo, cart = make_cart(tmp_path)
    cart.add_item('USB-01', 3)
    cart.save()

    cart.load()
    cart.load()

    assert cart.lines[0].quantity == 3

# Tests repository.get_product: SQL injection no longer works 
def test_get_product_blocks_sql_injection(tmp_path):
    repo, cart = make_cart(tmp_path)

    result = repo.get_product("' OR '1'='1")

    assert result is None

# Tests repository.get_saved_cart: SQL injection no longer works 
def test_get_saved_cart_blocks_sql_injection(tmp_path):
    repo, cart = make_cart(tmp_path)
    cart.add_item('USB-01', 1)
    cart.save()

    result = repo.get_saved_cart("x' OR '1'='1")

    assert result == []

# Tests repository.list_orders: only that user's orders 
def test_list_orders_only_shows_own_orders(tmp_path):
    repo, cart = make_cart(tmp_path)
    repo.save_order('alice', 10, 'paid', 'a1')
    repo.save_order('bob', 20, 'paid', 'b1')

    orders = repo.list_orders('alice')

    assert len(orders) == 1

# Tests repository.update_stock: refuses to go below 0
def test_update_stock_never_negative(tmp_path):
    repo, cart = make_cart(tmp_path)

    result = repo.update_stock('MOU-01', 25)

    assert result is False
    assert repo.get_product('MOU-01').stock == 20

# Tests setup_db: request_id is UNIQUE, so the database blocks duplicate orders
def test_database_blocks_duplicate_request_id(tmp_path):
    repo, cart = make_cart(tmp_path)
    repo.save_order('alice', 10, 'paid', 'same-id')

    with pytest.raises(sqlite3.IntegrityError):  
        repo.save_order('alice', 10, 'paid', 'same-id')

# Tests checkout: a paid order empties the cart AND removes the coupon
def test_paid_checkout_clears_cart_and_coupon(tmp_path):
    repo, cart = make_cart(tmp_path)
    cart.add_item('MOU-01', 2)
    cart.apply_discount('WELCOME10')

    result = CheckoutService(repo, FakePaymentGateway()).checkout(cart, 'TEST_TOKEN', 'r1')

    assert result.status == 'paid'
    assert cart.lines == []
    assert cart.discount_code is None
    assert repo.get_product('MOU-01').stock == 18

# Tests checkout: declined card gives stock back and keeps the cart 
def test_declined_payment_keeps_stock_and_cart(tmp_path):
    repo, cart = make_cart(tmp_path)
    cart.add_item('MOU-01', 2)
    declining_gateway = FakePaymentGateway(should_approve=False)

    result = CheckoutService(repo, declining_gateway).checkout(cart, 'TEST_TOKEN', 'r1')

    assert result.status == 'declined'
    assert repo.get_product('MOU-01').stock == 20
    assert len(cart.lines) == 1

# Tests checkout: gateway crash gives stock back and keeps the cart 
def test_payment_crash_keeps_stock_and_cart(tmp_path):
    repo, cart = make_cart(tmp_path)
    cart.add_item('MOU-01', 2)

    result = CheckoutService(repo, BrokenGateway()).checkout(cart, 'TEST_TOKEN', 'r1')

    assert result.status == 'payment_error'
    assert repo.get_product('MOU-01').stock == 20
    assert len(cart.lines) == 1

# Tests checkout: if stock ran out, stop before charging and give back reserved items
def test_out_of_stock_does_not_charge(tmp_path):
    repo, cart = make_cart(tmp_path)
    cart.add_item('MOU-01', 2)
    cart.add_item('USB-01', 3)
    repo.update_stock('USB-01', 49)
    gateway = FakePaymentGateway()

    result = CheckoutService(repo, gateway).checkout(cart, 'TEST_TOKEN', 'r1')

    assert result.status == 'out_of_stock'
    assert gateway.calls == []
    assert repo.get_product('MOU-01').stock == 20

# Tests checkout: same request_id twice only charges once
def test_repeated_checkout_charges_once(tmp_path):
    repo, cart = make_cart(tmp_path)
    cart.add_item('MOU-01', 2)
    gateway = FakePaymentGateway()
    service = CheckoutService(repo, gateway)

    first = service.checkout(cart, 'TEST_TOKEN', 'r1')
    second = service.checkout(cart, 'TEST_TOKEN', 'r1')

    assert second.order_id == first.order_id
    assert len(gateway.calls) == 1
    assert repo.get_product('MOU-01').stock == 18

# Tests checkout: payment token is no longer printed 
def test_payment_token_not_printed(tmp_path, capsys):
    repo, cart = make_cart(tmp_path)
    cart.add_item('USB-01', 1)

    CheckoutService(repo, FakePaymentGateway()).checkout(cart, 'SECRET_TOKEN', 'r1')

    printed = capsys.readouterr().out
    assert 'SECRET_TOKEN' not in printed