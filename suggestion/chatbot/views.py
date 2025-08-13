from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Place, FAQ
from math import radians, cos, sin, asin, sqrt
import difflib
import re

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1 
    dlon = lon2 - lon1 
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r

class ChatbotMessageAPIView(APIView):
    INTENTS = {
        "greeting": {
            "keywords": ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'hiya', 'howdy', 'greetings'],
            "response": "Hello! Welcome to our service. How can I help you today?"
        },
        "thanks": {
            "keywords": ['thanks', 'thank you', 'thx', 'ty', 'appreciate it'],
            "response": "You're welcome! If you have any questions, feel free to ask."
        },
        "goodbye": {
            "keywords": ['bye', 'goodbye', 'see you', 'later', 'take care', 'farewell'],
            "response": "Goodbye! Have a great day!"
        },
        "smalltalk": {
            "keywords": ['how are you', 'how is it going', 'hows it going', 'whats up'],
            "response": "I’m just a bot, but I’m doing great! How about you?"
        },
        "help": {
            "keywords": ['help', 'assist me', 'can you help me', 'what can you do'],
            "response": "I can help you find nearby places, answer FAQs, or provide info about our services."
        },
        "yes": {
            "keywords": ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay'],
            "response": "Great! Let's continue. What do you want to know?"
        },
        "no": {
            "keywords": ['no', 'nah', 'nope'],
            "response": "Alright. If you change your mind, I’m here to help."
        }
    }

    CATEGORIES = {
    "park": ["park", "gardens", "green area", "picnic spot", "playground"],
    "museum": ["museum", "gallery", "exhibition", "art place", "history center"],
    "restaurant": ["restaurant", "diner", "eatery", "cafe", "coffee shop", "bistro", "food place"],
    "shopping": ["shopping mall", "mall", "marketplace", "bazaar", "shops", "stores", "shopping center"],
    "lake": ["lake", "pond", "reservoir", "waterbody"],
    "adventure": ["adventure park", "amusement park", "funfair", "waterpark", "theme park", "rides"],
    "relaxation": ["relaxation", "spa", "wellness", "meditation", "yoga"],
    "kids": ["kids", "children", "play area", "kid friendly"],
    "family friendly": ["family friendly", "family trip", "family outing"],
    "romantic": ["romantic", "date spot", "couples", "love spot"],
    "quiet": ["quiet", "peaceful", "calm", "serene"],
    "photography": ["photography", "photo spot", "instagrammable", "scenic view"]
     }

    MOODS = {
        'romantic': 'romantic',
        'friends': 'friends',
        'family': 'family friendly',
        'photography': 'photography',
        'quiet': 'quiet',
    }

    def clean_message(self, message: str):
        message = str(message).strip().lower()
        message = re.sub(r'[^\w\s]', '', message)  # Remove punctuation
        message = re.sub(r'\s+', ' ', message)     # Collapse spaces
        return message

    def find_intent(self, message: str):
        for intent, data in self.INTENTS.items():
            for keyword in data['keywords']:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, message):
                    return intent, data['response']
        return None, None

    def validate_location(self, lat, lon):
        if lat is None or lon is None:
            return False, Response({"type": "location_request", "reply": "Please share your location (latitude and longitude) for this request."})
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            return True, (lat_f, lon_f)
        except (ValueError, TypeError):
            return False, Response({"type": "error", "reply": "Invalid latitude or longitude values."}, status=status.HTTP_400_BAD_REQUEST)

    def filter_places_by_category(self, user_lat, user_lon, category):
        places = Place.objects.filter(category__icontains=category)
        matched_places = []
        for place in places:
            try:
                dist_km = haversine(user_lat, user_lon, place.latitude, place.longitude)
                matched_places.append({
                    "name": place.name,
                    "category": place.category or "General",
                    "distance_km": round(dist_km, 2)
                })
            except Exception:
                continue
        matched_places.sort(key=lambda x: x['distance_km'])
        return matched_places

    def post(self, request) -> Response:
        raw_message = request.data.get('message', '')
        message = self.clean_message(raw_message)
        user_lat = request.data.get('latitude')
        user_lon = request.data.get('longitude')

        if not message:
            return Response({"type": "error", "reply": "Please send a message."},
                            status=status.HTTP_400_BAD_REQUEST)

        # 1. Check basic intents
        intent, reply = self.find_intent(message)
        if intent:
            return Response({"type": intent, "reply": reply})

        # --- Detect filters first ---
        hours = None
        max_distance = None

        time_match = re.search(r'(\d+)\s*hour', message)
        if time_match:
            hours = int(time_match.group(1))

        dist_match = re.search(r'(?:within\s*)?(\d+)\s*km|(\d+)\s*km\s*distance|distance\s*(\d+)\s*km', message)
        if dist_match:
            for group in dist_match.groups():
                if group:
                    max_distance = float(group)
                    break

        # If hours or distance filter exists, apply both together
        if hours or max_distance:
            valid, result = self.validate_location(user_lat, user_lon)
            if not valid:
                return result
            user_lat, user_lon = result

            places = Place.objects.all()
            filtered_places = []
            for place in places:
                try:
                    dist_km = haversine(user_lat, user_lon, place.latitude, place.longitude)
                    duration = getattr(place, 'average_duration', 1)

                    if (hours is None or duration <= hours) and (max_distance is None or dist_km <= max_distance):
                        filtered_places.append({
                            "name": place.name,
                            "category": place.category or "General",
                            "distance_km": round(dist_km, 2),
                            "duration_hours": duration
                        })
                except Exception:
                    continue

            filtered_places.sort(key=lambda x: x['distance_km'])
            if not filtered_places:
                filters_text = []
                if hours:
                    filters_text.append(f"{hours} hours")
                if max_distance:
                    filters_text.append(f"{max_distance} km")
                return Response({"type": "multi_filter_places",
                                "places": [],
                                "reply": f"Sorry, no places found matching {', '.join(filters_text)}."})

            reply_parts = []
            if hours:
                reply_parts.append(f"within {hours} hours")
            if max_distance:
                reply_parts.append(f"within {max_distance} km")
            reply_msg = f"Here are some places {', '.join(reply_parts)}:\n" + "\n".join(
                [f"{i+1}. {p['name']} ({p['category']}) - {p['distance_km']} km, {p['duration_hours']} hour(s)"
                for i, p in enumerate(filtered_places[:5])]
            )
            return Response({"type": "multi_filter_places", "places": filtered_places[:5], "reply": reply_msg})

        # 2. Nearest places (if no hours/distance filter)
        if any(word in message for word in ['nearest', 'nearby', 'closest', 'near me', 'nearby me', 'suggest', 'visit', 'visiting']):
            valid, result = self.validate_location(user_lat, user_lon)
            if not valid:
                return result
            user_lat, user_lon = result

            places = Place.objects.all()
            places_with_distance = []
            for place in places:
                try:
                    dist = haversine(user_lat, user_lon, place.latitude, place.longitude)
                    places_with_distance.append((dist, place))
                except Exception:
                    continue

            places_with_distance.sort(key=lambda x: x[0])
            nearest = places_with_distance[:5]

            if not nearest:
                return Response({"type": "nearest_places", "places": [], "reply": "Sorry, I couldn't find any nearby places."})

            reply_msg = "Here are some nearest places you can visit:\n" + "\n".join(
                [f"{i+1}. {place.name} ({place.category or 'General'}) - {round(dist, 2)} km away"
                for i, (dist, place) in enumerate(nearest)]
            )

            places_data = [{
                "name": place.name,
                "category": place.category or "General",
                "distance_km": round(dist, 2)
            } for dist, place in nearest]

            return Response({
                "type": "nearest_places",
                "places": places_data,
                "reply": reply_msg
            })

        # 3. Category detection with synonyms
        for category, keywords in self.CATEGORIES.items():
            if any(word in message for word in keywords):
                valid, result = self.validate_location(user_lat, user_lon)
                if not valid:
                    return result
                user_lat, user_lon = result
                matched_places = self.filter_places_by_category(user_lat, user_lon, category)
                if not matched_places:
                    return Response({
                        "type": "category_places",
                        "places": [],
                        "reply": f"Sorry, no {category} places found near you."
                    })
                reply_msg = f"Here are some {category} places near you:\n" + "\n".join(
                    [f"{i+1}. {p['name']} - {p['distance_km']} km away"
                    for i, p in enumerate(matched_places[:5])]
                )
                return Response({
                    "type": "category_places",
                    "places": matched_places[:5],
                    "reply": reply_msg
                })

        # 4. Mood detection
        for mood_key, mood_category in self.MOODS.items():
            if mood_key in message:
                valid, result = self.validate_location(user_lat, user_lon)
                if not valid:
                    return result
                user_lat, user_lon = result
                mood_places = self.filter_places_by_category(user_lat, user_lon, mood_category)
                if not mood_places:
                    return Response({"type": "mood_places", "places": [], "reply": f"Sorry, no places found for {mood_key} mood near you."})
                reply_msg = f"Here are some places perfect for {mood_key}:\n" + "\n".join(
                    [f"{i+1}. {p['name']} - {p['distance_km']} km away" for i, p in enumerate(mood_places[:5])]
                )
                return Response({"type": "mood_places", "places": mood_places[:5], "reply": reply_msg})

        # 5. Open hours / travel mode placeholders
        if 'open now' in message or 'open at' in message or 'open today' in message:
            return Response({"type": "open_hours", "reply": "Opening hours info is coming soon!"})
        if 'by car' in message or 'by bike' in message or 'by walk' in message or 'walking distance' in message:
            return Response({"type": "travel_mode", "reply": "Travel mode filtering will be available soon!"})

        # 6. FAQ matching
        faqs = FAQ.objects.all()
        faq_questions = [faq.question.lower() for faq in faqs]
        matches = difflib.get_close_matches(message, faq_questions, n=1, cutoff=0.4)
        if matches:
            matched_question = matches[0]
            try:
                answer = faqs.get(question__iexact=matched_question).answer
                return Response({"type": "faq", "reply": answer})
            except FAQ.DoesNotExist:
                pass

        # 7. Fallback
        fallback_reply = (
            "Sorry, I couldn't understand your question.\n"
            "You can ask me things like:\n"
            "- 'I have 5 hours to visit'\n"
            "- 'Find parks near me'\n"
            "- 'Places within 5 km'\n"
            "- 'Help'\n"
            "- 'What services do you provide?'\n"
            "- Or ask FAQs about our places."
        )
        return Response({"type": "fallback", "reply": fallback_reply})


class NearestPlacesAPIView(APIView):
    def post(self, request) -> Response:
        user_lat = request.data.get('latitude')
        user_lon = request.data.get('longitude')

        if user_lat is None or user_lon is None:
            return Response({"error": "Latitude and Longitude required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_lat = float(user_lat)
            user_lon = float(user_lon)
        except (ValueError, TypeError):
            return Response({"error": "Invalid latitude or longitude"}, status=status.HTTP_400_BAD_REQUEST)

        places = Place.objects.all()
        places_with_distance = []
        
        for place in places:
            try:
                dist = haversine(user_lat, user_lon, place.latitude, place.longitude)
                places_with_distance.append((dist, place))
            except Exception:
                continue
        
        places_with_distance.sort(key=lambda x: x[0])
        nearest = places_with_distance[:5]

        data = []
        for dist, place in nearest:
            data.append({
                "name": place.name,
                "category": place.category if place.category else "General",
                "distance_km": round(dist, 2),
            })

        return Response(data)