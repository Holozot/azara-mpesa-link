from django.shortcuts import render, redirect
from carts.models import CartItem
from .forms import OrderForm
from .models import Order, OrderProduct, Payment
from django.contrib.auth.decorators import login_required
from decimal import Decimal
import datetime 

@login_required(login_url='login')
def place_order(request, total=0, quantity=0):
    current_user = request.user

    # 1. Check Cart
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store:store')

    # 2. Calculate Totals
    grand_total = 0
    tax = 0
    for cart_item in cart_items:
        total += cart_item.sub_total()
        quantity += cart_item.quantity
    grand_total = total + tax

    # 3. Handle Form
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # A. Create Order
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.estate = form.cleaned_data['estate']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.grand_total = grand_total
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()
            
            # B. Generate Order Number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr,mt,dt)
            current_date = d.strftime("%Y%m%d") 
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            # C. CREATE ORDER PRODUCTS 
            for item in cart_items:
                order_product = OrderProduct()
                order_product.order_id = data.id
                order_product.user_id = request.user.id
                order_product.product_id = item.product_id
                order_product.quantity = item.quantity
                order_product.product_price = item.product.price
                
                # Save Variant info if it exists
                product_variation = item.variations.first()
                if product_variation:
                    order_product.product_variant = product_variation
                    order_product.variant_details = str(product_variation) # Save as text backup

                order_product.save()

            # D. Load the Payment Page
            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'grand_total': grand_total,
            }
            return render(request, 'orders/order_detail.html', context)
            
        else:
            return redirect('cart:checkout')
            
    return redirect('cart:checkout')

@login_required(login_url='login')
def order_complete(request):
    order_number = request.GET.get('order_number')
    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order=order)
        
        context = {
            'order': order,
            'ordered_products': ordered_products,
            'subtotal': order.order_total, 
        }
        return render(request, 'orders/order_complete.html', context)
    
    except (Payment.DoesNotExist, Order.DoesNotExist):
        return redirect('store:store')