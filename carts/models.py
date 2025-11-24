from django.db import models
from store.models import Product, ProductVariant
from accounts.models import Account # <--- Import your custom User model

# 1. THE CART
class Cart(models.Model):
    cart_id = models.CharField(max_length=250, blank=True)
    date_added = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.cart_id

# 2. THE CART ITEM
# 2. CartItem Model
class CartItem(models.Model):
    user = models.ForeignKey(Account, on_delete=models.CASCADE, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # The variations field is a ManyToMany relationship to hold selected variants (like size/color).
    variations = models.ManyToManyField(ProductVariant, blank=True) 
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, null=True)
    quantity = models.IntegerField()
    is_active = models.BooleanField(default=True)

    # Helper method to calculate the subtotal for this specific cart item (qty * price)
    def sub_total(self):
        # We assume the CartItem holds only ONE variant (size/price) in its variations field.
        # We fetch the first variant to get its price.
        variant = self.variations.first()
        
        # Use the price from the ProductVariant object
        if variant:
            return variant.price * self.quantity
        else:
            # Fallback if no variant is selected/found (should not happen in a complete flow)
            return self.product.get_display_price * self.quantity 

    def __unicode__(self):
        return self.product