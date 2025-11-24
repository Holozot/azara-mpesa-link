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

    # 1. Check if cart is empty
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store:store')

    # 2. Calculate Totals (Tax removed)
    grand_total = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity
    
    # Grand total is simply the total of products
    grand_total = total 

    # 3. Process Form
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # --- Create Order ---
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.estate = form.cleaned_data['estate']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            
            # Handle Delivery Selection
            delivery_method = request.POST.get('delivery_method')
            data.delivery_method = delivery_method
            if delivery_method == 'Pickup':
                data.estate = 'Pickup Location'
                data.city = 'Nairobi'

            # Save Financials (Tax removed)
            data.order_total = grand_total
            data.grand_total = grand_total
            data.ip = request.META.get('REMOTE_ADDR')
            
            # Generate Order Number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr, mt, dt)
            current_date = d.strftime("%Y%m%d")
            timestamp = datetime.datetime.now().strftime("%H%M%S")
            order_number = f"{current_date}{current_user.id}{timestamp}"
            data.order_number = order_number
            
            data.save()

            # --- Create Pending Payment Record ---
            payment = Payment(
                user = current_user,
                payment_id = f"MPESA-{order_number}", 
                payment_method = 'M-Pesa',
                amount_paid = str(grand_total),
                status = 'Pending', 
            )
            payment.save()
            
            data.payment = payment
            data.is_ordered = False
            data.save()

            # --- Save Order Products ---
            for item in cart_items:
                order_product = OrderProduct()
                order_product.order = data
                order_product.payment = payment
                order_product.user = current_user
                order_product.product = item.product
                order_product.quantity = item.quantity
                order_product.product_price = item.product.price
                order_product.ordered = False
                
                # Handle Variants if they exist
                variant = item.variations.first()
                if variant:
                    order_product.product_price = variant.price
                    order_product.variant_details = variant.size_ml_g
                
                order_product.save()
                
                # Reduce Stock
                if variant:
                    variant.stock -= item.quantity
                    variant.save()
                else:
                    item.product.stock -= item.quantity
                    item.product.save()

            # Clear Cart
            CartItem.objects.filter(user=request.user).delete()

            # --- REDIRECT TO M-PESA PAGE ---
            return redirect('order_review', order_id=data.id)
        else:
            print("Form errors:", form.errors) 
            return redirect('checkout') 
    else:
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