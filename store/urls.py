from django.urls import path
from . import views # We need to import the views from the current directory

app_name = 'store'

urlpatterns = [
    # 1. HOME PAGE URL: Maps the root URL (/) to the new 'home' view
    # This renders templates/home.html
    path('', views.home, name='home'),
    
    # 2. SHOP ALL/DEFAULT STORE PAGE URL: Maps /store/ to the 'store' view
    # This renders templates/store/store.html
    path('store/', views.store, name='store'), 

    # 3. CATEGORY FILTERING PATH:
    # This is the path used by the links in navbar.html to filter products.
    path('store/<slug:category_slug>/', views.store, name='products_by_category'),
    
    # 4. PRODUCT DETAIL PATH: (Crucial for linking products from home/store pages)
    # Ensure this path is defined so the URL tag in home.html works.
    path('store/<slug:category_slug>/<slug:product_slug>/', views.product_detail, name='product_detail'),

    # 5. SEARCH URL: Maps /search/ to the new search view
    path('search/', views.search, name='search'),

    # 6. M-PESA Callback (This is the URL Safaricom hits)
    path('mpesa/callback/', views.stk_push_callback, name='mpesa_callback'),
    
    # 7. Trigger STK Push (The actual payment action)
    path('mpesa/stk_push/<int:order_id>/', views.stk_push_request, name='stk_push_request'),
    
    # 8. Order Review Page (Where the payment form lives)
    path('order/review/<int:order_id>/', views.order_detail_view, name='order_review'),
    
    # 9. Order Receipt/History (After payment)
    path('order/receipt/<int:order_id>/', views.order_receipt_view, name='order_receipt'),
    
    # 10. Success Notification Page
    path('order/complete/<int:order_id>/', views.order_complete_view, name='order_complete'),
    
    # 11. User's Order History Dashboard
    path('orders/', views.my_orders_view, name='my_orders'),
    
    # 12. Dummy Payment Handler (Redirects to real flow for safety)
    path('payment/dummy/<int:order_id>/', views.dummy_payment_request, name='dummy_payment_request'),
]
