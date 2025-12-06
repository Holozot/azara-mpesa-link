from django.shortcuts import render, redirect, get_object_or_404
from .forms import RegistrationForm, UserForm # <--- Added UserForm
from .models import Account
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required 
from django.contrib.auth.hashers import make_password, check_password
from carts.models import Cart, CartItem
from carts.views import _cart_id
from orders.models import Order
import requests 

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
            
            # --- CRITICAL FIX: Capture Security Q/A ---
            security_question = form.cleaned_data['security_question']
            security_answer = form.cleaned_data['security_answer']

            encrypted_answer = make_password(security_answer.lower())

            # Create user
            user = Account.objects.create_user(
                first_name=first_name, 
                last_name=last_name, 
                email=email, 
                username=username, 
                password=password
            )
            
            user.phone_number = phone_number
            user.security_question = security_question
            user.security_answer = encrypted_answer
            
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

# --- LOGIN VIEW ---
def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        user = authenticate(email=email, password=password)

        if user is not None:
            
            # STEP 1: GET THE GUEST CART *BEFORE* LOGIN
            try:
                cart = Cart.objects.get(cart_id=_cart_id(request))
                is_cart_item_exists = CartItem.objects.filter(cart=cart).exists()
            except Cart.DoesNotExist:
                cart = None
                is_cart_item_exists = False

            # STEP 2: LOG THE USER IN
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
                pass # Fallback to standard redirect
            
            return redirect('store:store') # Or 'dashboard'
                
        else:
            messages.error(request, 'Invalid login credentials')
            return redirect('login') 

    return render(request, 'accounts/login.html')

# --- FORGOT PASSWORD STEP 1: VALIDATE EMAIL ---
def reset_password_validate(request):
    if request.method == 'POST':
        email = request.POST['email']
        try:
            user = Account.objects.get(email=email)
            # Store the user ID in session to use in the next step
            request.session['reset_user_id'] = user.id
            return redirect('security_question_step')
        except Account.DoesNotExist:
            messages.error(request, 'This email does not exist.')
            return redirect('reset_password_validate')
            
    return render(request, 'accounts/reset_password_1.html')

# --- FORGOT PASSWORD STEP 2: ASK QUESTION ---
def security_question_step(request):
    # Get the user from the session
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('reset_password_validate')
    
    user = Account.objects.get(id=user_id)
    
    if request.method == 'POST':
        answer = request.POST['security_answer']
        new_password = request.POST['new_password']
        confirm_password = request.POST['confirm_password']
        
        if not check_password(answer.lower().strip(), user.security_answer):
            messages.error(request, "Incorrect answer to security question.")
            return redirect('security_question_step')
            
        # Check Password Match
        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('security_question_step')
            
        # SUCCESS: Update Password
        user.set_password(new_password)
        user.save()
        messages.success(request, "Password reset successfully! Please login.")
        del request.session['reset_user_id'] 
        return redirect('login')

    # Get the readable version of the question
    question_label = user.get_security_question_display()
    
    context = {
        'question': question_label,
    }
    return render(request, 'accounts/reset_password_2.html', context)

# --- EDIT PROFILE ---
@login_required(login_url='login')
def edit_profile(request):
    user_account = get_object_or_404(Account, id=request.user.id)
    
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user_account)
        if user_form.is_valid():
            user_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('edit_profile')
    else:
        # Load the form with existing data
        user_form = UserForm(instance=user_account)

    context = {
        'user_form': user_form,
    }
    return render(request, 'accounts/edit_profile.html', context)

# --- LOGOUT VIEW ---
def logout(request):
    auth_logout(request)
    messages.success(request, 'You are logged out.')
    return redirect('login')

# --- DASHBOARD VIEW ---
@login_required(login_url='login')
def dashboard(request):
    user_orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
    orders_count = user_orders.count()
    
    context = {
        'orders_count': orders_count,
    }
    return render(request, 'accounts/dashboard.html', context)