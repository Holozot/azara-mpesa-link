from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),

    path('dashboard/', views.dashboard, name='dashboard'), 
    path('', views.dashboard, name='dashboard'), # This makes /accounts/ go to dashboard too
    
    
    path('forgotPassword/', views.forgotPassword, name='forgotPassword'),
    
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    
    path('reset-security-check/', views.security_question_step, name='security_question_step'),

    path('change_password/', views.change_password, name='change_password'),
]