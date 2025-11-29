from django.shortcuts import render, redirect
from .forms import RegistrationForm
from .models import Account
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required 
from carts.models import Cart, CartItem
from carts.views import _cart_id
import requests # Needed for URL parsing 

# --- REGISTER VIEW ---
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            username = form.cleaned_data['username']

            # Create user
            user = Account.objects.create_user(
                first_name=first_name, 
                last_name=last_name, 
                email=email, 
                username=username, 
                password=password
            )
            
            user.phone_number = phone_number
            user.is_active = True 
            
            user.save()

            messages.success(request, 'Registration successful. You can now log in.')
            return redirect('login')
    else:
        form = RegistrationForm()
        
    context = {
        'form': form,
    }
    return render(request, 'accounts/register.html', context)

# --- LOGIN VIEW (With Cart Merge Logic) ---
def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        user = authenticate(email=email, password=password)

        if user is not None:
            
            # STEP 1: GET THE GUEST CART *BEFORE* LOGIN
            # Do this because auth_login() changes the Session ID
            try:
                # Capture the cart object associated with the OLD session
                cart = Cart.objects.get(cart_id=_cart_id(request))
                is_cart_item_exists = CartItem.objects.filter(cart=cart).exists()
            except Cart.DoesNotExist:
                cart = None
                is_cart_item_exists = False

            # STEP 2: LOG THE USER IN
            # Rotates the session ID, but we already grabbed the 'cart' object above
            auth_login(request, user)
            
            # STEP 3: PERFORM THE MERGE
            if is_cart_item_exists and cart:
                guest_cart_items = CartItem.objects.filter(cart=cart)
                
                for item in guest_cart_items:
                    # Check if user already has this product
                    existing_user_item = CartItem.objects.filter(product=item.product, user=user)
                    
                    # Sort guest variations for comparison
                    guest_variations = list(item.variations.all())
                    guest_variations.sort(key=lambda x: x.id)
                    
                    match_found = False
                    
                    if existing_user_item.exists():
                        for usr_item in existing_user_item:
                            # Sort user variations
                            user_variations = list(usr_item.variations.all())
                            user_variations.sort(key=lambda x: x.id)
                            
                            if guest_variations == user_variations:
                                # MATCH FOUND: Add quantity and delete guest item
                                usr_item.quantity += item.quantity
                                usr_item.save()
                                item.delete()
                                match_found = True
                                break
                    
                    if not match_found:
                        # NO MATCH: Move guest item to user
                        item.user = user
                        item.cart = None # Detach from session cart
                        item.save()

            messages.success(request, 'You are now logged in.')
            
            # --- REDIRECT LOGIC ---
            url = request.META.get('HTTP_REFERER')
            try:
                query = requests.utils.urlparse(url).query
                params = dict(x.split('=') for x in query.split('&'))
                if 'next' in params:
                    nextPage = params['next']
                    return redirect(nextPage)
            except:
                return redirect('store:home')
                
        else:
            messages.error(request, 'Invalid login credentials')
            return redirect('login') 

    return render(request, 'accounts/login.html')

# --- LOGOUT VIEW ---
def logout(request):
    auth_logout(request)
    messages.success(request, 'You are logged out.')
    return redirect('login')

# --- DASHBOARD VIEW ---
@login_required(login_url='login') 
def dashboard(request):
    return render(request, 'accounts/dashboard.html')