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

            # Define 'order' variable here 
            order = data 

            # C. CREATE ORDER PRODUCTS 
            # This loop must be indented INSIDE the 'if form.is_valid()' block
            for item in cart_items:
                # 1. CREATE the object
                orderproduct = OrderProduct()

                # 2. Fill details
                orderproduct.order_id = order.id  # Now 'order' exists!
                orderproduct.user_id = request.user.id
                orderproduct.product_id = item.product_id
                orderproduct.quantity = item.quantity
                
                # 3. Get the specific Variant (Size)
                variant = item.variations.first()
                
                # 4. Save Price AND the Link to the Variant
                if variant:
                    orderproduct.product_price = variant.price 
                    orderproduct.product_variant = variant  # <--- THIS IS THE FIX
                    
                    # Optional: Snapshot the name so it stays forever
                    orderproduct.variant_details = variant.size_ml_g 
                else:
                    # Fallback if no variant found (shouldn't happen)
                    orderproduct.product_price = 0 

                # 5. Save to database
                orderproduct.ordered = True
                orderproduct.save()

            # D. Load the Payment Page or Trigger M-Pesa
            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'grand_total': grand_total,
            }
            return render(request, 'orders/order_detail.html', context)
            
        else:
            # Form invalid
            return redirect('checkout') # Or print(form.errors)
            
    return redirect('checkout')

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