from django.shortcuts import render, redirect
from .forms import RegistrationForm
from .models import Account
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout

# --- FIX 1: ADD THIS IMPORT ---
from django.contrib.auth.decorators import login_required 
# ------------------------------

def register(request):
    # --- 1. HANDLE POST REQUEST (Form Submission) ---
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
            pass

    # --- 2. HANDLE GET REQUEST ---
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
            auth_login(request, user)
            messages.success(request, 'You are now logged in.')
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

# --- FIX 2: DASHBOARD MUST BE UNINDENTED (At the same level as logout) ---
@login_required(login_url='login') 
def dashboard(request):
    return render(request, 'accounts/dashboard.html')