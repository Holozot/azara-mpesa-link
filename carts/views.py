from django.shortcuts import render, redirect, get_object_or_404
from store.models import Product, ProductVariant
from .models import Cart, CartItem
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from decimal import Decimal # Required for accurate monetary calculations

# Helper function to get cart totals (
def get_cart_totals(cart_items):
    sub_total = Decimal('0.00')
    
    for cart_item in cart_items:
        # Use Decimal for accurate calculations
        sub_total += cart_item.sub_total()
    
    # Grand total currently equals subtotal (excluding offline delivery charges)
    grand_total = sub_total
    
    # Return as strings for template display convenience
    return {
        'sub_total': f'{sub_total:.2f}',
        'grand_total': f'{grand_total:.2f}',
    }


def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart

def add_cart(request, product_id):
    current_user = request.user
    product = get_object_or_404(Product, id=product_id) 
    
    # 1. Get Selected Variant
    product_variant = None
    if request.method == 'POST':
        try:
            variant_id = request.POST['variant_id']
            # NOTE: Assuming ProductVariant has a single variant type (e.g., size) 
            # and that 'variations' on CartItem is a ManyToManyField linked to ProductVariant.
            product_variant = ProductVariant.objects.get(id=variant_id) 
        except Exception:
            messages.error(request, 'Please select a size.')
            return redirect(product.get_url())

    # --- LOGIC FOR LOGGED IN USERS ---
    if current_user.is_authenticated:
        # Check if this item is already in the user's cart
        is_cart_item_exists = CartItem.objects.filter(product=product, user=current_user).exists()
        
        if is_cart_item_exists:
            cart_items = CartItem.objects.filter(product=product, user=current_user)
            # Check existing items to see if variant matches
            existing_variant_list = []
            id_list = []
            for item in cart_items:
                # The logic below relies on variations.all() returning a specific order/count, 
                # which can be brittle. We are retaining your original logic structure 
                # but flagging it for potential future cleanup if needed.
                existing_variant = item.variations.all()
                existing_variant_list.append(list(existing_variant))
                id_list.append(item.id)

            if [product_variant] in existing_variant_list:
                # Increase quantity
                index = existing_variant_list.index([product_variant])
                item_id = id_list[index]
                item = CartItem.objects.get(product=product, id=item_id)
                item.quantity += 1
                item.save()
            else:
                # New variant for existing product
                item = CartItem.objects.create(product=product, quantity=1, user=current_user)
                item.variations.add(product_variant)
                item.save()
        else:
            # New Item entirely
            item = CartItem.objects.create(product=product, quantity=1, user=current_user)
            item.variations.add(product_variant)
            item.save()
            
        return redirect('cart')

    # --- LOGIC FOR GUEST USERS (Not Logged In) ---
    else:
        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
        except Cart.DoesNotExist:
            cart = Cart.objects.create(cart_id = _cart_id(request))
            cart.save()

        is_cart_item_exists = CartItem.objects.filter(product=product, cart=cart).exists()
        
        if is_cart_item_exists:
            cart_items = CartItem.objects.filter(product=product, cart=cart)
            existing_variant_list = []
            id_list = []
            for item in cart_items:
                existing_variant = item.variations.all()
                existing_variant_list.append(list(existing_variant))
                id_list.append(item.id)

            if [product_variant] in existing_variant_list:
                index = existing_variant_list.index([product_variant])
                item_id = id_list[index]
                item = CartItem.objects.get(product=product, id=item_id)
                item.quantity += 1
                item.save()
            else:
                item = CartItem.objects.create(product=product, quantity=1, cart=cart)
                item.variations.add(product_variant)
                item.save()
        else:
            item = CartItem.objects.create(product=product, quantity=1, cart=cart)
            item.variations.add(product_variant)
            item.save()
            
        return redirect('cart')

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
        pass # Silently fail if the item isn't found
        
    return redirect('cart')


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
        pass # Silently fail if the item isn't found
        
    return redirect('cart')


def cart(request, total=0, quantity=0, cart_items=None):
    try:
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        
        for cart_item in cart_items:
            # This line already correctly uses the sub_total() helper (which we just fixed in the model)
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

        # Calculate all totals needed for the summary section on checkout.html
        # This will now use the corrected get_cart_totals function.
        total_cart_data = get_cart_totals(cart_items)

        context = {
            'cart_items': cart_items,
            'total_cart_data': total_cart_data,
        }
        
        return render(request, 'orders/checkout.html', context)

    except Exception as e:
        # Simple error handling
        print(f"Error in checkout view: {e}")
        return redirect('cart')