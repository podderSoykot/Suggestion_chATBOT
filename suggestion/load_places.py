import os
import django
import json

# --- Setup Django environment ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'suggestion.settings')  # Change 'suggestion' to your Django project name
django.setup()

from chatbot.models import Place

# --- Path to your JSON file ---
JSON_FILE_PATH = r"D:\Soykot_Podder_Lead_AI_Engineer\Suggestion_chATBOT\suggestion\places.json"

def load_places():
    with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
        places = json.load(f)

    for place in places:
        obj, created = Place.objects.get_or_create(
            name=place['name'],
            defaults={
                'latitude': place['latitude'],
                'longitude': place['longitude'],
                'category': place.get('category', ''),
            }
        )
        if created:
            print(f"Added place: {obj.name}")
        else:
            print(f"Place already exists: {obj.name}")

if __name__ == '__main__':
    load_places()
