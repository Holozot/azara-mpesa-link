from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # --- STANDARD STORE URLS ---
    path('', views.home, name='home'),
    path('store/', views.store, name='store'),
    path('store/<slug:category_slug>/', views.store, name='products_by_category'),
    path('store/<slug:category_slug>/<slug:product_slug>/', views.product_detail, name='product_detail'),
    path('search/', views.search, name='search'),

    # --- M-PESA & ORDER URLS ---
    path('mpesa/callback/', views.stk_push_callback, name='mpesa_callback'),
    path('mpesa/stk_push/<int:order_id>/', views.stk_push_request, name='stk_push_request'),
    
    # The Review Page (Payment Entry)
    path('order/review/<int:order_id>/', views.order_detail_view, name='order_review'),
    
    # The Receipt (After Payment)
    path('order/receipt/<int:order_id>/', views.order_receipt_view, name='order_receipt'),
    
    # The Success Notification
    path('order/complete/<int:order_id>/', views.order_complete_view, name='order_complete'),
    
    # Dashboard History
    path('orders/', views.my_orders_view, name='my_orders'),
]