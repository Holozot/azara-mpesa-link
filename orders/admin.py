from django.contrib import admin
from .models import Order, OrderProduct, Payment

# 1. INLINE: Shows products inside the 'Order' page
class OrderProductInline(admin.TabularInline):
    model = OrderProduct

    readonly_fields = ('user', 'product', 'product_variant', 'variant_details', 'quantity', 'product_price', 'ordered')
    extra = 0

# 2. ORDER ADMIN: The main Order table
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'full_name', 'phone', 'email', 'city', 'order_total', 'status', 'is_ordered', 'created_at']
    list_filter = ['status', 'is_ordered']
    search_fields = ['order_number', 'first_name', 'last_name', 'phone', 'email']
    list_per_page = 20
    inlines = [OrderProductInline] # Connects the inline above

    def full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'

# 3. ORDER PRODUCT ADMIN (NEW): The separate "Items Sold" table
class OrderProductAdmin(admin.ModelAdmin):
    # Helper to show the date from the parent Order
    def order_date(self, obj):
        return obj.order.created_at
    order_date.short_description = 'Date Bought'

    list_display = ['user', 'product', 'quantity', 'product_price', 'order_date', 'ordered']
    list_filter = ['ordered', 'user']
    search_fields = ['order__order_number', 'user__username', 'product__product_name']

# 4. PAYMENT ADMIN
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'user', 'payment_method', 'amount_paid', 'status', 'created_at']

# --- REGISTRATION ---
admin.site.register(Order, OrderAdmin)
# UPDATE THIS LINE to use the new class
admin.site.register(OrderProduct, OrderProductAdmin) 
admin.site.register(Payment, PaymentAdmin)