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
]