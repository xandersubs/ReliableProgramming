"""Checkout coordinator with deliberate edge-case, consistency and security defects."""
from models import OrderResult


class CheckoutService:
    def __init__(self, repository, payment_gateway):
        self.repository = repository
        self.payment_gateway = payment_gateway

    def checkout(self, cart, payment_token, request_id):
        if request_id:
            existing = self.repository.get_order_by_request_id(request_id)
            if existing:
                return OrderResult(*existing) 
        #These changes to the above lines along with the changes made in repository.py and setup_db.py prevent the previous error where a retry or a double-click with the same request_id charged the card again and took the stock again the old amount > 1000 block only printed messages and did nothing now checkout() looks up the request_id first and returns the existing order if there is one and request_id TEXT UNIQUE in the schema is in place to ensure the database itself rejects duplicate orders

        if len(cart.lines) == 0:
            return OrderResult(None, 'empty', 0)
        amount = cart.total()
        #payment token used to be printed but thats a sensitive data leak because if the console and logs show Charging payment token:<token> anyone could see it

        #Previously if stock was sold out between adding an item to the cart and checking out the order was still charged but now if update_stock returns False the code releases what it already reserved and returns out_of_stock before charging
        reserved = []
        for line in cart.lines:
            if not self.repository.update_stock(line.sku, line.quantity):
                self._release(reserved)
                return OrderResult(None,'out_of_stock', amount)
            reserved.append(line)
        try:
            response = self.payment_gateway.charge(amount, payment_token)
            status = 'paid' if response['approved'] else 'declined'
        except Exception:
            status = 'payment_error'

        #previously stock was reduced before charging and never put back so a declined card or a gateway crash permanently removed stock that was never sold but now stock is reserved then charged then released if the payment fails this is done by reserving lines tracked in a list and _release() adds them back by calling update_stock(sku, -quantity)
        if status != 'paid':
            self._release(reserved) 
    
        order_id = self.repository.save_order(cart.user_id, amount, status, request_id)

        if status == 'paid':
            cart.lines.clear()  
            cart.discount_code = None
            cart.save()
            #Previously after a card was declined the cart was cleared and the empty cart was saved so the customer had to start over but now the cart is cleared and saved only if the order is paid for aswell the coupon is also cleared after a paid order so it can't carry over to the next one
        return OrderResult(order_id, status, amount)

    def _release(self, lines):
        for line in lines:
            self.repository.update_stock(line.sku, -line.quantity)
    
