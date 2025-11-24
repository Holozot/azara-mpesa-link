from django.db import models
from django.urls import reverse

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
    
    # --- CHANGE: Images go to 'photos' folder ---
    image = models.ImageField(upload_to='photos') 
    
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)
        index_together = (('id', 'slug'),)

    def __str__(self):
        return f"{self.brand.name} - {self.name}"

    # --- ADDED: This is required for links to work ---
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

# 4. PRODUCT VARIANT MODEL (This replaces 'Variation')
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