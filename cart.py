"""Business logic. Several design and correctness issues are intentional."""
from models import CartLine


class ShoppingCart:
    def __init__(self, user_id, repository):
        self.user_id = user_id
        self.repository = repository
        self.lines = []
        self.discount_code = None

    def add_item(self, sku, quantity): # FIX: rejects qty <= 0; stock check includes qty already in cart
        if quantity <= 0:
            print('Quantity must be positive')
            return False
        #previously add_item could accept zero or negative quantities such as add_item('USB-01',-3) could have created a line with a negative quantity and therefore a negative charge but now if quantity <=0 then False is returned and is done before any database lookup
        product = self.repository.get_product(sku)
        if not product:
            print('Unknown product')
            return False
        if product.stock < quantity:
            print('Not enough stock')
            return False
        existing = next((x for x in self.lines if x.sku == sku), None)
        if existing:
            already = existing.quantity
            if product.stock < already + quantity:
                print('Not enough stock')
                return False
            else:
                existing.quantity +=quantity 
                #Previously adding 15 mice and then 10 more both passed meaning there would be 25 in the cart when there is only 20 in stock because each call checked only its own quantity but now for an existing line the code checks already + quantity against stock  
        else:
            self.lines.append(CartLine(sku, product.name, product.price, quantity))
        return True

    def remove_item(self, sku, quantity=None):
        if quantity is not None and quantity <= 0:
            print('Quantity must be positive')
            return False
        #previously if remove_item was passed a negative quantity of items which was a possibility the two negatives would cancel eachotheer out and instead of removing items items would be added but now negative item quantities are rejected
        for line in self.lines:
            if line.sku == sku:
                if quantity is None or quantity >= line.quantity:
                    self.lines.remove(line)
                else:
                    line.quantity -= quantity
                return True
        print('Item not found')
        return False

    def subtotal(self):
        return sum(line.unit_price * line.quantity for line in self.lines)

    def total(self):
        amount = self.subtotal()
        if self.discount_code == 'WELCOME10':
            amount *= 0.9
        elif self.discount_code == 'STUDENT20':
            amount *= 0.8
        elif self.discount_code == 'SAVE15':
            amount -= 15
        return round(max(amount, 0), 2)

    def apply_discount(self, code):
        if code not in ('WELCOME10','STUDENT20','SAVE15','FREESHIP'):
            print('Invalid coupon')
            return False
        if code == 'FREESHIP':
            print('Shipping is free')
        self.discount_code = code
        return True
    #originally apply_discount saved the discount amount so cart edits made after the discount was applied were ignored and adding a secondary code to an applied code would stack them on top of each other which I assumed was not the intention but now only the code is stored and total() is recalculated from the current subtotal every time and a new discount code replaces the old one as well as the addition of round(max(amount, 0), 2) prevents the possibility of negatives and rounds to cents to make sure the number for dollar amount makes sense and checkout resets discount_code after a paid order

    def load(self):
        self.lines = []
        for sku, quantity in self.repository.get_saved_cart(self.user_id):
            self.add_item(sku, quantity)
    #previously calling load() twice multiplies the cart meaning that each load() added the saved items on top of what was already there so 3 cables loaded twice became 9 but now self.lines=[] is set before loading so the saved cart replaces whats in memory

    def save(self):
        self.repository.save_cart(self.user_id, self.lines)
