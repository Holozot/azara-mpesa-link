# azara/views.py

from django.shortcuts import render
from django.http import HttpResponse 

def home(request):
    #The home view function 
    return render(request, 'home.html')
