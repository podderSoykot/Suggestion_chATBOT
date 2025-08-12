from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Place, FAQ
from math import radians, cos, sin, asin, sqrt
import difflib
import re

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on the Earth (in kilometers)."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1 
    dlon = lon2 - lon1 
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # Earth radius in kilometers
    return c * r

class ChatbotMessageAPIView(APIView):
    def clean_message(self, message: str) -> str:
        """Normalize and clean the message text."""
        message = str(message).strip().lower()
        message = re.sub(r'[^\w\s]', '', message)  # Remove punctuation
        message = re.sub(r'\s+', ' ', message)     # Collapse multiple spaces
        return message

    def post(self, request) -> Response:
        raw_message = request.data.get('message', '')
        message = self.clean_message(raw_message)
        user_lat = request.data.get('latitude')
        user_lon = request.data.get('longitude')

        if not message:
            return Response(
                {"type": "error", "reply": "Please send a message."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Intent groups
        greetings = [
            'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
            'hiya', 'howdy', 'greetings'
        ]
        thanks = ['thanks', 'thank you', 'thx', 'thank you very much', 'ty', 'appreciate it']
        goodbyes = ['bye', 'goodbye', 'see you', 'later', 'take care', 'farewell']
        how_are_you = ['how are you', 'how is it going', 'hows it going', 'whats up']
        help_requests = ['help', 'assist me', 'can you help me', 'what can you do']
        yes_responses = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay']
        no_responses = ['no', 'nah', 'nope']

        # Match intents
        if any(msg in message for msg in greetings):
            return Response({"type": "greeting", "reply": "Hello! Welcome to our service. How can I help you today?"})

        if any(msg in message for msg in thanks):
            return Response({"type": "thanks", "reply": "You're welcome! If you have any questions, feel free to ask."})

        if any(msg in message for msg in goodbyes):
            return Response({"type": "goodbye", "reply": "Goodbye! Have a great day!"})

        if any(msg in message for msg in how_are_you):
            return Response({"type": "smalltalk", "reply": "I’m just a bot, but I’m doing great! How about you?"})

        if any(msg in message for msg in help_requests):
            return Response({
                "type": "help",
                "reply": "I can help you find nearby places, answer FAQs, or provide info about our services."
            })

        if message in yes_responses:
            return Response({"type": "yes", "reply": "Great! Let's continue. What do you want to know?"})

        if message in no_responses:
            return Response({"type": "no", "reply": "Alright. If you change your mind, I’m here to help."})

        # Detect time-based visit request like "I have 5 hours"
        time_match = re.search(r'(\d+)\s*hour', message)
        if time_match:
            hours = int(time_match.group(1))

            if user_lat is None or user_lon is None:
                return Response({
                    "type": "location_request",
                    "reply": "Please share your location (latitude and longitude) to find places you can visit within your available time."
                })

            try:
                user_lat = float(user_lat)
                user_lon = float(user_lon)
            except (ValueError, TypeError):
                return Response(
                    {"type": "error", "reply": "Invalid latitude or longitude values."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Filter places based on estimated_duration and distance (optional)
            places = Place.objects.all()
            possible_places = []

            for place in places:
                try:
                    distance_km = haversine(user_lat, user_lon, place.latitude, place.longitude)
                    duration = getattr(place, 'average_duration', 1)  # default 1 hour if missing
                    if duration <= hours:
                        possible_places.append({
                            "name": place.name,
                            "category": place.category if place.category else "General",
                            "distance_km": round(distance_km, 2),
                            "duration_hours": duration
                        })
                except Exception:
                    continue

            possible_places.sort(key=lambda x: x['distance_km'])

            if not possible_places:
                return Response({
                    "type": "time_based_places",
                    "places": [],
                    "reply": "Sorry, no places found within your available time."
                })

            reply_text = (
                f"You have {hours} hours available. Here are some places you can comfortably visit:\n" +
                "\n".join(
                    [f"{i+1}. {p['name']} ({p['category']}) - approx {p['duration_hours']} hour(s)" for i, p in enumerate(possible_places[:5])]
                ) +
                "\nEnjoy your trip! Let me know if you want recommendations for food, adventure, or relaxation."
            )

            return Response({
                "type": "time_based_places",
                "places": possible_places[:5],
                "reply": reply_text
            })

        # Detect request for nearest places (no time limit)
        nearest_place_keywords = [
            'nearest place', 'nearby place', 'places to visit', 'visit near me', 'near me',
            'around me', 'places nearby', 'close by', 'whats near', 'whats close to me'
        ]
        if any(keyword in message for keyword in nearest_place_keywords):
            if user_lat is None or user_lon is None:
                return Response({
                    "type": "location_request",
                    "reply": "Please share your location (latitude and longitude) to find nearby places."
                })

            try:
                user_lat = float(user_lat)
                user_lon = float(user_lon)
            except (ValueError, TypeError):
                return Response(
                    {"type": "error", "reply": "Invalid latitude or longitude values."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            places = Place.objects.all()
            places_with_distance = []
            for place in places:
                try:
                    distance_km = haversine(user_lat, user_lon, place.latitude, place.longitude)
                    places_with_distance.append((distance_km, place))
                except Exception:
                    continue

            places_with_distance.sort(key=lambda x: x[0])
            nearest_places = [
                {
                    "name": place.name,
                    "category": place.category if place.category else "General",
                    "distance_km": round(dist, 2)
                }
                for dist, place in places_with_distance[:5]
            ]

            if not nearest_places:
                return Response({
                    "type": "nearest_places",
                    "places": [],
                    "reply": "Sorry, I couldn't find any nearby places right now."
                })

            return Response({
                "type": "nearest_places",
                "places": nearest_places,
                "reply": "Here are some nearby places you can visit."
            })

        # FAQ fuzzy matching
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

        # Fallback
        return Response({
            "type": "fallback",
            "reply": (
                "Sorry, I couldn't understand your question.\n"
                "You can ask me things like:\n"
                "• 'nearest place' (share location)\n"
                "• 'I have 5 hours to visit'\n"
                "• 'help'\n"
                "• 'FAQ about [topic]'"
            )
        })

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
