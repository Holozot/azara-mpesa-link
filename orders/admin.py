from django.contrib import admin
from .models import Order, OrderProduct, Payment

class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    # ADD 'product_variant' and 'variant_details'  to see the Size/Color in the order
    readonly_fields = ('user', 'product', 'product_variant', 'variant_details', 'quantity', 'product_price', 'ordered')
    extra = 0

class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'full_name', 'phone', 'email', 'city', 'order_total', 'status', 'is_ordered', 'created_at']
    list_filter = ['status', 'is_ordered']
    search_fields = ['order_number', 'first_name', 'last_name', 'phone', 'email']
    list_per_page = 20
    inlines = [OrderProductInline]

    def full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'

class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'user', 'payment_method', 'amount_paid', 'status', 'created_at']

admin.site.register(Order, OrderAdmin)
admin.site.register(OrderProduct)
admin.site.register(Payment, PaymentAdmin)