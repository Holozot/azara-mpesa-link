from django.db import models
from django.urls import reverse
from django.conf import settings 

# 1. CATEGORY MODEL
class Category(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, unique=True)
    parent = models.ForeignKey('self', related_name='children', on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        ordering = ('name',)
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def get_url(self):
        return reverse('store:products_by_category', args=[self.slug])

    def __str__(self):
        return self.name

# 2. BRAND MODEL
class Brand(models.Model):
    name = models.CharField(max_length=100, db_index=True, unique=True)

    class Meta:
        ordering = ('name',)
        verbose_name = 'brand'
        verbose_name_plural = 'brands'

    def __str__(self):
        return self.name

# 3. PRODUCT MODEL
class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, related_name='products', on_delete=models.CASCADE) 
    
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, db_index=True)
    description = models.TextField() 
    
    # Images go to 'photos' folder
    image = models.ImageField(upload_to='photos') 
    
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)
        index_together = (('id', 'slug'),)

    def __str__(self):
        return f"{self.brand.name} - {self.name}"

    def get_url(self):
        return reverse('store:product_detail', args=[self.category.slug, self.slug])

    # Logic to fetch price from variants
    @property
    def get_display_price(self):
        cheapest_variant = self.variants.filter(is_active=True).order_by('price').first()
        return cheapest_variant.price if cheapest_variant else 0.00
    
    # Logic to fetch size from variants
    @property
    def get_display_size(self):
        cheapest_variant = self.variants.filter(is_active=True).order_by('price').first()
        return cheapest_variant.size_ml_g if cheapest_variant else "N/A"

# 4. PRODUCT VARIANT MODEL
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    size_ml_g = models.CharField(max_length=50, verbose_name='Size (ml/g/oz)', help_text="e.g., 450ml, 261g")
    price = models.DecimalField(max_digits=10, decimal_places=2) # Price in KES
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('product', 'size_ml_g')

    def __str__(self):
        return f"{self.product.name} - {self.size_ml_g}"

# --- REMOVED: Order and OrderProduct classes (They are now in orders/models.py) ---

# 5. MPESA TRANSACTION MODEL
class MpesaTransaction(models.Model):
    # CHANGED: 'orders.Order' points to the Order model in the 'orders' app
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='mpesa_transactions')
    
    checkout_request_id = models.CharField(max_length=100, unique=True)
    merchant_request_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    mpesa_receipt_number = models.CharField(max_length=20, blank=True, null=True)
    transaction_date = models.DateTimeField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    status = models.CharField(max_length=20, default='Pending') # Pending, Successful, Failed
    result_desc = models.TextField(blank=True, null=True) # Error message from M-PESA if any
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"M-PESA {self.mpesa_receipt_number or 'Pending'} - {self.status}"