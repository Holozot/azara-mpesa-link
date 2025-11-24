from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
import json
import logging
import datetime
from .mpesa_utils import initiate_stk_push

# 1. Models that are still in the 'store' app
from .models import Product, Category, MpesaTransaction 

from orders.models import Order 
# -------------------------

logger = logging.getLogger(__name__)

# --- HELPER FUNCTION ---
def get_diverse_products(parent_slug):
    """
    Fetches up to 4 products, prioritizing one from each sub-category.
    """
    diverse_products = []
    try:
        parent_cat = Category.objects.get(slug=parent_slug)
        children = parent_cat.children.all()
        
        for child in children:
            product = Product.objects.filter(category=child, available=True).order_by('-created').first()
            if product:
                diverse_products.append(product)
            if len(diverse_products) >= 4:
                break
        
        if len(diverse_products) < 4:
            existing_ids = [p.id for p in diverse_products]
            needed_count = 4 - len(diverse_products)
            extras = Product.objects.filter(
                Q(category=parent_cat) | Q(category__parent=parent_cat),
                available=True
            ).exclude(id__in=existing_ids).order_by('-created')[:needed_count]
            diverse_products.extend(extras)
            
    except Category.DoesNotExist:
        pass

    return diverse_products


# 1. STORE VIEW
def store(request, category_slug=None):
    categories = Category.objects.all()
    products = None
    current_category = 'All Products' 

    if category_slug != None:
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
            category = get_object_or_404(Category, slug=category_slug)
            products = Product.objects.filter(
                Q(category=category) | Q(category__parent=category),
                available=True
            ).order_by('-created')
            current_category = category.name
    else:
        products = Product.objects.filter(available=True).order_by('-created')

    paginator = Paginator(products, 6) 
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)
    
    product_count = products.count()

    context = {
        'products': paged_products, 
        'categories': categories,
        'product_count': product_count,
        'current_category': current_category,
    }
    return render(request, 'store/store.html', context)


# 2. HOME VIEW
def home(request):
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
        single_product = Product.objects.get(
            category__slug=category_slug,
            slug=product_slug,
            available=True
        )
        variants = single_product.variants.filter(is_active=True)
        
    except Exception as e:
        raise e

    categories = Category.objects.all()

    context = {
        'single_product': single_product,
        'variants': variants,
        'categories': categories,
    }
    return render(request, 'store/product_detail.html', context)


# 4. SEARCH VIEW
def search(request): 
    products = None
    product_count = 0
    categories = Category.objects.all() 

    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.filter(
                Q(description__icontains=keyword) | 
                Q(name__icontains=keyword) | 
                Q(category__name__icontains=keyword),
                available=True
            ).order_by('-created')
            product_count = products.count()
            current_category = f"Search results for: '{keyword}'"
        else:
            current_category = 'All Products'
    else:
        current_category = 'All Products'


    context = {
        'products': products,
        'product_count': product_count,
        'categories': categories,
        'current_category': current_category,
    }
    return render(request, 'store/store.html', context)


# --- REAL M-PESA & ORDER LOGIC ---

def my_orders_view(request):
    """Shows real orders from the database."""
    orders = Order.objects.all().order_by('-created_at')
    context = {'orders': orders}
    return render(request, 'store/my_orders.html', context)


def order_detail_view(request, order_id):
    """
    Renders the Order Review page where the Payment Form is embedded.
    """
    order = get_object_or_404(Order, id=order_id)
    
    # If already paid, go straight to receipt
    if order.status == 'PAID':
        return redirect('order_receipt', order_id=order.id)
        
    return render(request, 'store/order_detail.html', {'order': order})


def stk_push_request(request, order_id):
    """Triggers the real M-PESA STK Push."""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        phone = request.POST.get('phone_number') # Get phone from form
        amount = int(order.grand_total)

        response = initiate_stk_push(phone, amount, order.id)
        
        if response and response.get('ResponseCode') == '0':
            # Save tracking ID
            checkout_req_id = response.get('CheckoutRequestID')
            MpesaTransaction.objects.create(
                order=order,
                checkout_request_id=checkout_req_id,
                amount=amount,
                status='Pending'
            )
            return render(request, 'store/stk_push_sent.html', {'order': order})
        else:
            error = response.get('CustomerMessage', 'Failed to initiate.')
            return render(request, 'store/stk_push_failed.html', {'error': error})

    # If for some reason this is accessed via GET, redirect back to review page
    return redirect('order_review', order_id=order.id)


@csrf_exempt
def stk_push_callback(request):
    """M-PESA talks to this view to confirm payment."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f"M-PESA DATA: {data}")
            
            stk_callback = data.get('Body', {}).get('stkCallback', {})
            checkout_req_id = stk_callback.get('CheckoutRequestID')
            result_code = stk_callback.get('ResultCode')
            
            transaction = MpesaTransaction.objects.get(checkout_request_id=checkout_req_id)
            
            if result_code == 0:
                metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                receipt_no = next((item['Value'] for item in metadata if item['Name'] == 'MpesaReceiptNumber'), None)
                
                transaction.status = 'Successful'
                transaction.mpesa_receipt_number = receipt_no
                transaction.save()
                
                order = transaction.order
                order.status = 'PAID'
                order.save()
            else:
                transaction.status = 'Failed'
                transaction.save()
            
        except Exception as e:
            logger.error(f"Error: {e}")
            
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


def order_complete_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    transaction = MpesaTransaction.objects.filter(order=order, status='Successful').first()
    
    context = {
        'order': order,
        'receipt_number': transaction.mpesa_receipt_number if transaction else "Pending/Failed"
    }
    return render(request, 'store/order_complete.html', context)


def order_receipt_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    transaction = MpesaTransaction.objects.filter(order=order, status='Successful').first()
    
    context = {
        'order': order,
        'receipt_number': transaction.mpesa_receipt_number if transaction else "N/A",
        'payment_date': transaction.transaction_date if transaction else order.created_at
    }
    return render(request, 'store/order_receipt.html', context)

# --- DUMMY URL HANDLER (Redirects to real flow) ---
def dummy_payment_request(request, order_id):
    return redirect('order_review', order_id=order_id)