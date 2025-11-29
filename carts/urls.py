from django.urls import path
from . import views

# THIS IS CRITICAL: It defines the namespace 'cart' used in your templates
app_name = 'cart'

urlpatterns = [
    # Path for the main cart page
    path('', views.cart, name='cart'),
    
    # Path to add an item to the cart (Increment quantity)
    path('add_cart/<int:product_id>/', views.add_cart, name='add_cart'),
    
    # Path to decrease item quantity (Minus button)
    path('remove_cart/<int:product_id>/<int:cart_item_id>/', views.remove_cart, name='remove_cart'),
    
    # Path to delete the item completely (The Remove Button)
    path('remove_cart_item/<int:product_id>/<int:cart_item_id>/', views.remove_cart_item, name='remove_cart_item'),

    # Checkout Path
    path('checkout/', views.checkout, name='checkout'),
]