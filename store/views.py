from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import json
import logging
import datetime
from .mpesa_utils import initiate_stk_push
from carts.models import CartItem 

# --- IMPORTS ---
from .models import Product, Category, Brand, ProductVariant, MpesaTransaction 
from orders.models import Order , Payment
# ---------------

logger = logging.getLogger(__name__)

# --- HELPER FUNCTION: Get Diverse Products ---
def get_diverse_products(parent_slug):
    diverse_products = []
    try:
        parent_cat = Category.objects.get(slug=parent_slug)
        children = parent_cat.children.all()
        for child in children:
            product = Product.objects.filter(category=child, available=True).order_by('-created').first()
            if product: diverse_products.append(product)
            if len(diverse_products) >= 4: break
        
        if len(diverse_products) < 4:
            existing_ids = [p.id for p in diverse_products]
            needed_count = 4 - len(diverse_products)
            extras = Product.objects.filter(Q(category=parent_cat) | Q(category__parent=parent_cat), available=True).exclude(id__in=existing_ids).order_by('-created')[:needed_count]
            diverse_products.extend(extras)
    except Category.DoesNotExist: pass
    return diverse_products

# --- HELPER FUNCTION: Apply Filters (Shared by Store & Search) ---
def apply_product_filters(request, products):
    """
    Applies Brand and Price filters to a product queryset.
    Returns: (filtered_products, selected_brand_ids)
    """
    # 1. Brand Filter
    selected_brand_ids = request.GET.getlist('brands')
    if selected_brand_ids:
        products = products.filter(brand__id__in=selected_brand_ids)

    # 2. Price Filter (Variant-First Logic)
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    # Treat empty strings as None
    if min_price == '': min_price = None
    if max_price == '': max_price = None

    if min_price or max_price:
        # Start with all variants (using objects.all() to be safe against inactive ones)
        variants_query = ProductVariant.objects.all()
        
        if min_price:
            variants_query = variants_query.filter(price__gte=min_price)
        if max_price:
            variants_query = variants_query.filter(price__lte=max_price)

        # Get IDs of products that match these specific variant constraints
        matched_product_ids = variants_query.values_list('product_id', flat=True)
        products = products.filter(id__in=matched_product_ids)

    # 3. Deduping
    products = products.distinct()
    
    return products, selected_brand_ids

# 1. STORE VIEW
def store(request, category_slug=None):
    categories = Category.objects.all()
    products = None
    current_category = 'All Products' 

    # --- 1. Base Query (Category Logic) ---
    if category_slug != None:
        if category_slug == 'haircare':
            try:
                hair_cat = Category.objects.get(slug='haircare')
                products = Product.objects.filter(Q(category=hair_cat) | Q(category__parent=hair_cat), available=True).order_by('-created')
                current_category = hair_cat.name
            except Category.DoesNotExist: 
                products = Product.objects.none()
        elif category_slug == 'skincare':
            try:
                skin_cat = Category.objects.get(slug='skincare')
                products = Product.objects.filter(Q(category=skin_cat) | Q(category__parent=skin_cat), available=True).order_by('-created')
                current_category = skin_cat.name
            except Category.DoesNotExist: 
                products = Product.objects.none()
        else:
            category = get_object_or_404(Category, slug=category_slug)
            products = Product.objects.filter(Q(category=category) | Q(category__parent=category), available=True).order_by('-created')
            current_category = category.name
    else:
        products = Product.objects.filter(available=True).order_by('-created')

    # --- 2. DYNAMIC BRANDS ---
    relevant_brand_ids = products.values_list('brand_id', flat=True).distinct()
    all_brands = Brand.objects.filter(id__in=relevant_brand_ids).order_by('name')

    # --- 3. Apply Filters (Brand Selection & Price) ---
    # Now we filter the products based on user selection
    products, selected_brand_ids = apply_product_filters(request, products)

    # --- 4. Pagination Helper ---
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    current_filters = query_params.urlencode()

    # --- 5. Pagination ---
    paginator = Paginator(products, 6) 
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)
    product_count = products.count()

    context = {
        'products': paged_products, 
        'categories': categories, 
        'product_count': product_count, 
        'current_category': current_category,
        'all_brands': all_brands, # This is now the filtered list
        'selected_brand_ids': list(map(int, selected_brand_ids)), 
        'current_filters': current_filters,
    }
    return render(request, 'store/store.html', context)

# 2. HOME VIEW
def home(request):
    haircare_products = get_diverse_products('haircare')
    skincare_products = get_diverse_products('skincare')
    return render(request, 'home.html', {'haircare_products': haircare_products, 'skincare_products': skincare_products})

# 3. PRODUCT DETAIL VIEW
def product_detail(request, category_slug, product_slug):
    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug, available=True)
        variants = single_product.variants.filter(is_active=True)
    except Exception as e: raise e
    categories = Category.objects.all()
    return render(request, 'store/product_detail.html', {'single_product': single_product, 'variants': variants, 'categories': categories})

# 4. SEARCH VIEW
def search(request): 
    products = Product.objects.none()
    product_count = 0
    categories = Category.objects.all() 
    current_category = 'All Products'
    
    # --- 1. Base Search Query ---
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.filter(Q(description__icontains=keyword) | Q(name__icontains=keyword) | Q(category__name__icontains=keyword), available=True).order_by('-created')
            current_category = f"Search results for: '{keyword}'"
    
    # --- 2. Apply Filters (Brand & Price) ---
    products, selected_brand_ids = apply_product_filters(request, products)
    all_brands = Brand.objects.all()

    # --- 3. Pagination Helper ---
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    current_filters = query_params.urlencode()

    # --- 4. Pagination ---
    paginator = Paginator(products, 6) 
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)
    product_count = products.count()

    context = {
        'products': paged_products, 
        'product_count': product_count, 
        'categories': categories, 
        'current_category': current_category,
        'all_brands': all_brands,
        'selected_brand_ids': list(map(int, selected_brand_ids)),
        'current_filters': current_filters,
    }
    return render(request, 'store/store.html', context)

# --- REAL M-PESA & ORDER LOGIC ---
@login_required(login_url='login')
def my_orders_view(request):
    """
    Shows orders belonging to the logged-in user.
    """
    # Fetch orders belonging to the user, ordered by newest first
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
    
    context = {
        'orders': orders,
    }
    return render(request, 'store/my_orders.html', context)

def order_detail_view(request, order_id):
    """Renders the Order Review page where the Payment Form is embedded."""
    order = get_object_or_404(Order, id=order_id)
    if order.status == 'PAID':
        return redirect('store:order_receipt', order_id=order.id)
    return render(request, 'orders/order_detail.html', {'order': order})

def stk_push_request(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        phone = request.POST.get('phone_number')
        amount = int(order.grand_total)
        
        # 1. Initiate M-Pesa
        response = initiate_stk_push(phone, amount, order.id)
        
        if response and response.get('ResponseCode') == '0':
            checkout_req_id = response.get('CheckoutRequestID')
            
            # 2. Create Transaction Record
            MpesaTransaction.objects.create(
                order=order,
                checkout_request_id=checkout_req_id,
                amount=amount,
                phone_number=phone,
                status='Pending'
            )
            
            # 3. RENDER THE SENT STK PUSH PAGE
            return render(request, 'store/stk_push_sent.html', {'order': order})
            
        else:
            # 4. RENDER THE "FAILED" PAGE (Immediate connection error)
            error = response.get('CustomerMessage', 'Failed to initiate M-Pesa.')
            return render(request, 'store/stk_push_failed.html', {'error': error})

    return redirect('store:order_detail', order_id=order.id)

@csrf_exempt
def stk_push_callback(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            stk_callback = data.get('Body', {}).get('stkCallback', {})
            checkout_req_id = stk_callback.get('CheckoutRequestID')
            result_code = stk_callback.get('ResultCode') # 0 = Success, 1/1032 = Cancelled/Fail
            
            transaction = MpesaTransaction.objects.get(checkout_request_id=checkout_req_id)
            order = transaction.order
            
            if result_code == 0:
                # --- SUCCESS SCENARIO ---
                metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                receipt_no = next((item['Value'] for item in metadata if item['Name'] == 'MpesaReceiptNumber'), None)
                
                # 1. Update Transaction
                transaction.status = 'Successful'
                transaction.mpesa_receipt_number = receipt_no
                transaction.save()
                
                # 2. Update Order
                order.payment = Payment.objects.create(
                    user=order.user,
                    payment_id=receipt_no,
                    payment_method='M-Pesa',
                    amount_paid=order.grand_total,
                    status='Completed'
                )
                order.is_ordered = True # Marks it as "Paid"
                order.status = 'Accepted'
                order.save()
                
                # 3. CLEAR THE CART ITEMS 
                # Filter by the user attached to the order
                CartItem.objects.filter(user=order.user).delete()
                
            else:
                # --- FAILURE SCENARIO ---
                # User cancelled or insufficient funds
                transaction.status = 'Failed'
                transaction.save()
                
                # The items remain in the cart so the user can try again.
                
        except Exception as e:
            logger.error(f"Error processing M-Pesa callback: {e}")
            
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

def order_complete_view(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        
        # Check if the Callback marked it as paid
        if order.is_ordered:
            # SUCCESS: Show the receipt
            transaction = MpesaTransaction.objects.filter(order=order, status='Successful').first()
            context = {
                'order': order,
                'receipt_number': transaction.mpesa_receipt_number if transaction else "N/A"
            }
            return render(request, 'orders/order_complete.html', context)
        else:
            # FAILURE/PENDING:
            # The callback hasn't arrived, or it failed.
            # Redirect to the Failure page so customer can try again.
            return render(request, 'store/stk_push_failed.html', {
                'error': 'Payment not received yet. You may have cancelled the request or M-Pesa is delayed.'
            })
            
    except Order.DoesNotExist:
        return redirect('store:home')

def order_receipt_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    transaction = MpesaTransaction.objects.filter(order=order, status='Successful').first()
    context = {'order': order, 'receipt_number': transaction.mpesa_receipt_number if transaction else "N/A", 'payment_date': transaction.transaction_date if transaction else order.created_at}
    return render(request, 'store/order_receipt.html', context)