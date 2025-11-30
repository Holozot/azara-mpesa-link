import os
import django
from django.core.management import call_command

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'azara.settings') # Change 'azara' if your project name is different
django.setup()

# Run the command safely
print("Exporting database to db.json...")
with open('db.json', 'w', encoding='utf-8') as f:
    call_command('dumpdata', exclude=['auth.permission', 'contenttypes'], stdout=f)
print("Done! Check your folder for db.json")