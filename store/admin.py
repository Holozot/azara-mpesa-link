from django.contrib import admin
from .models import Category, Brand, Product, ProductVariant

# Register Category and Brand simply
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name']

# Custom Admin Class for Product Variant
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1 # Show 1 extra empty form for easy addition of variants

# Custom Admin Class for Product
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'category', 'available', 'created']
    list_filter = ['available', 'created', 'brand', 'category']
    list_editable = ['available']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductVariantInline] # This links the variants directly to the product page

    # --- CUSTOM HELPERS ---
    
    # This fetches the price from the cheapest variant to show in the list
    def price_display(self, obj):
        return obj.get_display_price
    price_display.short_description = "Price"  # Sets the column header name

    # This sums up the stock from all variants (e.g., 500ml + 250ml)
    def stock_display(self, obj):
        # We use 'variants' because related_name='variants' in models.py
        return sum(v.stock for v in obj.variants.all())
    stock_display.short_description = "Total Stock"