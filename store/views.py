from django.shortcuts import render, get_object_or_404
from .models import Product, Category
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


# --- HELPER FUNCTION ---
def get_diverse_products(parent_slug):
    """
    Fetches up to 4 products, prioritizing one from each sub-category 
    to ensure variety on the homepage.
    """
    diverse_products = []
    try:
        parent_cat = Category.objects.get(slug=parent_slug)
        
        # 1. Get all sub-categories (children) of this parent
        children = parent_cat.children.all()
        
        # 2. Loop through each child and pick the newest product
        for child in children:
            product = Product.objects.filter(category=child, available=True).order_by('-created').first()
            if product:
                diverse_products.append(product)
            
            # Stop if we already have 4
            if len(diverse_products) >= 4:
                break
        
        # 3. FILLER LOGIC: If we found fewer than 4 products
        if len(diverse_products) < 4:
            # Get IDs of products we already picked so we don't pick them again
            existing_ids = [p.id for p in diverse_products]
            
            needed_count = 4 - len(diverse_products)
            
            # Find extras in the Parent category OR any Child category
            extras = Product.objects.filter(
                Q(category=parent_cat) | Q(category__parent=parent_cat),
                available=True
            ).exclude(id__in=existing_ids).order_by('-created')[:needed_count]
            
            # Add extras to the list
            diverse_products.extend(extras)
            
    except Category.DoesNotExist:
        pass

    return diverse_products


# 1. STORE VIEW
def store(request, category_slug=None):
    categories = Category.objects.all()
    products = None
    # CHANGE: Set default category name here
    current_category = 'All Products' 

    if category_slug != None:
        # Check for special hardcoded categories used in Home
        if category_slug == 'haircare':
            try:
                hair_cat = Category.objects.get(slug='haircare')
                products = Product.objects.filter(
                    Q(category=hair_cat) | Q(category__parent=hair_cat),
                    available=True
                ).order_by('-created')
                current_category = hair_cat.name
            except Category.DoesNotExist:
                 products = Product.objects.none()

        elif category_slug == 'skincare':
            try:
                skin_cat = Category.objects.get(slug='skincare')
                products = Product.objects.filter(
                    Q(category=skin_cat) | Q(category__parent=skin_cat),
                    available=True
                ).order_by('-created')
                current_category = skin_cat.name
            except Category.DoesNotExist:
                 products = Product.objects.none()
                 
        else:
            # Standard Category Behavior
            category = get_object_or_404(Category, slug=category_slug)
            
            # LOGIC: Show products in this category, OR products in its children
            products = Product.objects.filter(
                Q(category=category) | Q(category__parent=category),
                available=True
            ).order_by('-created')
            
            # CHANGE: Set category name for standard categories
            current_category = category.name
    else:
        # No Slug provided? Show ALL products
        products = Product.objects.filter(available=True).order_by('-created')

    # Pagination
    paginator = Paginator(products, 6) 
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)
    
    product_count = products.count()

    context = {
        'products': paged_products, 
        'categories': categories,
        'product_count': product_count,
        'current_category': current_category, # Pass to template
    }
    return render(request, 'store/store.html', context)


# 2. HOME VIEW
def home(request):
    # Use the helper function to get diverse lists based on Parent/Child logic
    haircare_products = get_diverse_products('haircare')
    skincare_products = get_diverse_products('skincare')

    context = {
        'haircare_products': haircare_products,
        'skincare_products': skincare_products,
    }
    return render(request, 'home.html', context)


# 3. PRODUCT DETAIL VIEW
def product_detail(request, category_slug, product_slug):
    try:
        # Fetch the product using both the category slug and the product slug
        single_product = Product.objects.get(
            category__slug=category_slug,
            slug=product_slug,
            available=True
        )
        # Get active variants for the product
        variants = single_product.variants.filter(is_active=True)
        
    except Exception as e:
        raise e

    # Fetch all categories for the shared navbar/footer links
    categories = Category.objects.all()

    context = {
        'single_product': single_product,
        'variants': variants,
        'categories': categories,
    }
    
    return render(request, 'store/product_detail.html', context)


# 4. SEARCH VIEW (Must be at the same indentation level as other functions)
def search(request): 
    products = None
    product_count = 0
    categories = Category.objects.all() 

    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.filter(
                Q(description__icontains=keyword) | 
                Q(name__icontains=keyword) |  # Changed from product_name to name
                Q(category__name__icontains=keyword), # Changed from category_name to name
                available=True
            ).order_by('-created')
            product_count = products.count()
            # CHANGE: Set category name for search results
            current_category = f"Search results for: '{keyword}'"
        else:
            # If keyword is empty, default to All Products
            current_category = 'All Products'
    else:
        current_category = 'All Products'


    context = {
        'products': products,
        'product_count': product_count,
        'categories': categories,
        'current_category': current_category,
    }
    # Render the store template as search results look like a store page
    return render(request, 'store/store.html', context)