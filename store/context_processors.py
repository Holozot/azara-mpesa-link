# store/context_processors.py
from .models import Category

def menu_links(request):
    # Fetch all categories from the database
    links = Category.objects.all()
    # Return them as a dictionary accessible to templates
    return dict(links=links)