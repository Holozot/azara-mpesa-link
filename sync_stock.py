import os
import django

# 1. Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'azara.settings')
django.setup()

from store.models import Product

def run():
    print("--- STARTING STOCK FIX ---")
    all_products = Product.objects.all()
    count = 0

    for p in all_products:
        variants = p.variants.all()
        
        # Only update if the product has variants
        if variants.exists():
            # Calculate total
            total_variant_stock = sum(v.stock for v in variants)
            
            # Update Parent
            p.stock = total_variant_stock
            p.save()
            
            print(f"FIXED: {p.name} -> Stock is now {total_variant_stock}")
            count += 1
        else:
            print(f"SKIPPED: {p.name} (No variants)")

    print(f"--- DONE. Updated {count} products. ---")

if __name__ == '__main__':
    run()