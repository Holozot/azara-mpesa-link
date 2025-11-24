from django.shortcuts import render, redirect
from carts.models import CartItem
from .models import Order, OrderProduct, Payment
from .forms import OrderForm
from store.models import Product, ProductVariant
from django.contrib.auth.decorators import login_required
from decimal import Decimal
import datetime 

# --- Helper Function for Order Calculations ---
def get_order_totals(cart_items):
    sub_total = Decimal('0.00')
    total_quantity = 0
    
    for item in cart_items:
        # Uses the sub_total() helper from CartItem model in carts/models.py
        sub_total += item.sub_total() 
        total_quantity += item.quantity
    
    # Grand total equals subtotal (Delivery/Tax handled offline or included)
    grand_total = sub_total
    
    return {
        'sub_total': f'{sub_total:.2f}',
        'grand_total': f'{grand_total:.2f}',
        'total_quantity': total_quantity
    }

# --- Main Views ---

@login_required(login_url='login')
def place_order(request):
    current_user = request.user
    
    # 1. Check if cart is empty
    cart_items = CartItem.objects.filter(user=current_user)
    if cart_items.count() <= 0:
        return redirect('store:store')

    # 2. Calculate Totals
    totals = get_order_totals(cart_items)
    grand_total = Decimal(totals['grand_total'])

    # 3. Process POST Request from Checkout Form
    if request.method == 'POST':
        form = OrderForm(request.POST)
        
        if form.is_valid():
            # --- Create the Order Object ---
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            
            # Handle Delivery Method Logic
            delivery_method = request.POST.get('delivery_method')
            data.delivery_method = delivery_method
            
            if delivery_method == 'Pickup':
                data.estate = 'Pickup'
                data.city = 'Store Location'
            else:
                data.estate = form.cleaned_data['estate']
                data.city = form.cleaned_data['city']
            
            data.order_total = grand_total
            data.ip = request.META.get('REMOTE_ADDR')
            
            # Generate Order Number (YYYYMMDD + UserID)
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr, mt, dt)
            current_date = d.strftime("%Y%m%d")
            order_number = current_date + str(current_user.id)
            data.order_number = order_number
            
            data.save()
            
            # Retrieve the created order to link payment/items
            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)

            # --- Create Payment Record (M-Pesa) ---
            payment = Payment(
                user = current_user,
                payment_id = f"MPESA-{order.order_number}", 
                payment_method = 'M-Pesa',
                amount_paid = str(grand_total),
                status = 'Pending', 
            )
            payment.save()
            
            # Link payment to order and mark as ordered
            order.payment = payment
            order.is_ordered = True
            order.save()

            # --- Move Cart Items to OrderProduct ---
            for item in cart_items:
                order_product = OrderProduct()
                order_product.order = order
                order_product.payment = payment
                order_product.user = request.user
                order_product.product = item.product
                order_product.quantity = item.quantity
                
                # Get price from variant if it exists
                variant = item.variations.first()
                if variant:
                    order_product.product_price = variant.price
                    order_product.variant_details = variant.size_ml_g
                    order_product.product_variant = variant
                else:
                    order_product.product_price = item.product.get_display_price

                order_product.product_name = item.product.name
                order_product.is_ordered = True
                order_product.save()
                
                # Reduce Stock
                if variant:
                    variant.stock -= item.quantity
                    variant.save()
                else:
                    item.product.stock -= item.quantity
                    item.product.save()

            # --- Clear Cart ---
            cart_items.delete()
            
            # --- Redirect to Success Page ---
            # We pass order_number as a GET parameter so the next view can look it up
            return redirect(f"{redirect('order_complete').url}?order_number={order.order_number}")
        
        else:
            print("Form errors:", form.errors) # Debugging: Print errors to console
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