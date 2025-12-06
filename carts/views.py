from django.shortcuts import render, redirect, get_object_or_404
from store.models import Product, ProductVariant
from .models import Cart, CartItem
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from decimal import Decimal 

# --- HELPER FUNCTIONS ---

def get_cart_totals(cart_items):
    sub_total = Decimal('0.00')
    for cart_item in cart_items:
        sub_total += cart_item.sub_total()
    
    grand_total = sub_total
    
    return {
        'sub_total': f'{sub_total:.2f}',
        'grand_total': f'{grand_total:.2f}',
    }

def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart

# --- VIEWS ---
def add_cart(request, product_id):
    current_user = request.user
    product = Product.objects.get(id=product_id) 
    
    # 1. INITIALIZE VARIABLES
    product_variation = []  
    product_quantity = 1 
    selected_variant = None 

    if request.method == 'POST':
        if 'quantity' in request.POST:
            product_quantity = int(request.POST['quantity'])
        
        variant_id = request.POST.get('variant_id')
        if variant_id:
            try:
                selected_variant = ProductVariant.objects.get(product=product, id=variant_id)
                product_variation.append(selected_variant)
            except:
                pass

    # LOGIC: DETERMINE WHICH STOCK TO CHECK
    if selected_variant:
        current_stock = selected_variant.stock
        stock_type = f"{selected_variant.size_ml_g}"
    else:
        current_stock = product.stock
        stock_type = "item"

    # RULE 1: HARD CHECK FOR EMPTY STOCK
    if current_stock <= 0:
        messages.warning(request, f'This {stock_type} is currently out of stock.')
        return redirect('store:store')

    # 2. DETERMINE CART
    if current_user.is_authenticated:
        cart_items_queryset = CartItem.objects.filter(product=product, user=current_user)
    else:
        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
        except Cart.DoesNotExist:
            cart = Cart.objects.create(cart_id=_cart_id(request))
        cart.save()
        cart_items_queryset = CartItem.objects.filter(product=product, cart=cart)

    # 3. CHECK IF ITEM EXISTS
    is_cart_item_exists = cart_items_queryset.exists()
    
    HOARDING_LIMIT = 5
    real_limit = min(HOARDING_LIMIT, current_stock)

    if is_cart_item_exists:
        ex_var_list = []
        id_list = []
        
        for item in cart_items_queryset:
            existing_variation = list(item.variations.all())
            existing_variation.sort(key=lambda x: x.id) 
            ex_var_list.append(existing_variation)
            id_list.append(item.id)

        product_variation.sort(key=lambda x: x.id)

        if product_variation in ex_var_list:
            # --- SCENARIO: ITEM EXISTS (INCREMENT) ---
            index = ex_var_list.index(product_variation)
            item_id = id_list[index]
            item = CartItem.objects.get(product=product, id=item_id)
            
            future_quantity = item.quantity + product_quantity
            
            if future_quantity > real_limit:
                # --- UPDATED MESSAGE LOGIC HERE ---
                if current_stock < HOARDING_LIMIT:
                    msg = f"Quantity exceeded available stock. Please select {current_stock} items or less."
                else:
                    msg = f"To avoid hoarding, you can only order {HOARDING_LIMIT} items of the same variant."
                
                messages.warning(request, msg)
                return redirect('cart:cart')
            
            item.quantity += product_quantity
            item.save()
            
        else:
            # --- SCENARIO: NEW VARIANT (CREATE) ---
            if product_quantity > real_limit:
                # --- UPDATED MESSAGE LOGIC HERE ---
                if current_stock < HOARDING_LIMIT:
                    msg = f"Quantity exceeded available stock. Please select {current_stock} items or less."
                else:
                    msg = f"To avoid hoarding, you can only order {HOARDING_LIMIT} items of the same variant."
                
                messages.warning(request, msg)
                return redirect('cart:cart')

            if current_user.is_authenticated:
                item = CartItem.objects.create(product=product, quantity=product_quantity, user=current_user)
            else:
                item = CartItem.objects.create(product=product, quantity=product_quantity, cart=cart)
            
            if len(product_variation) > 0:
                item.variations.clear()
                item.variations.add(*product_variation)
            item.save()
            
    else:
        # --- SCENARIO: NEW PRODUCT (CREATE) ---
        if product_quantity > real_limit:
            # --- UPDATED MESSAGE LOGIC HERE ---
            if current_stock < HOARDING_LIMIT:
                msg = f"Quantity exceeded available stock. Please select {current_stock} items or less."
            else:
                msg = f"To avoid hoarding, you can only order {HOARDING_LIMIT} items of the same variant."
            
            messages.warning(request, msg)
            return redirect('cart:cart')

        if current_user.is_authenticated:
            cart_item = CartItem.objects.create(
                product = product,
                quantity = product_quantity,
                user = current_user,
            )
        else:
            cart_item = CartItem.objects.create(
                product = product,
                quantity = product_quantity,
                cart = cart,
            )
            
        if len(product_variation) > 0:
            cart_item.variations.clear()
            cart_item.variations.add(*product_variation)
        cart_item.save()
    
    return redirect('carts:cart')


def remove_cart(request, product_id, cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    
    try:
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(product=product, user=request.user, id=cart_item_id)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
            
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            # If quantity is 1, remove the item completely
            cart_item.delete()
            
    except CartItem.DoesNotExist:
        pass 
        
    return redirect('carts:cart')

def remove_cart_item(request, product_id, cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    
    try:
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(product=product, user=request.user, id=cart_item_id)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
            
        # Delete the cart item regardless of quantity
        cart_item.delete()
        
    except CartItem.DoesNotExist:
        pass 
        
    return redirect('carts:cart')


def cart(request, total=0, quantity=0, cart_items=None):
    try:
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        
        for cart_item in cart_items:
            item_sub_total = cart_item.sub_total() 
            total += item_sub_total
            quantity += cart_item.quantity
            
    except ObjectDoesNotExist:
        pass
        
    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
    }
    return render(request, 'carts/cart.html', context)

@login_required(login_url='login')
def checkout(request):
    try:
        current_user = request.user
        cart_items = CartItem.objects.filter(user=current_user, is_active=True)
        cart_count = cart_items.count()
        
        if cart_count == 0:
            return redirect('store:store')

        total_cart_data = get_cart_totals(cart_items)

        context = {
            'cart_items': cart_items,
            'total_cart_data': total_cart_data,
        }
        
        return render(request, 'orders/checkout.html', context)

    except Exception as e:
        print(f"Error in checkout view: {e}")
        return redirect('cart:cart')