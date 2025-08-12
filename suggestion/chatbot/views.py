from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Place, FAQ
from math import radians, cos, sin, asin, sqrt
import difflib

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
    """
    API view to handle chatbot messages:
    - Handles greetings, thanks, goodbyes.
    - Returns nearest places if location and keywords detected.
    - Fuzzy matches FAQ questions for answers.
    - Otherwise fallback reply.
    """

    def post(self, request) -> Response:
        message = request.data.get('message', '').strip().lower()
        user_lat = request.data.get('latitude')
        user_lon = request.data.get('longitude')

        if not message:
            return Response({"reply": "Please send a message."}, status=status.HTTP_400_BAD_REQUEST)

        # Simple conversational intents
        greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening']
        thanks = ['thanks', 'thank you', 'thx', 'thank you very much']
        goodbyes = ['bye', 'goodbye', 'see you', 'later']

        if any(greet in message for greet in greetings):
            return Response({"reply": "Hello! Welcome to our service. How can I help you today?"})

        if any(thank in message for thank in thanks):
            return Response({"reply": "You're welcome! If you have any questions, feel free to ask."})

        if any(bye in message for bye in goodbyes):
            return Response({"reply": "Goodbye! Have a great day!"})

        # Detect request for nearest places
        nearest_place_keywords = ['nearest place', 'nearby place', 'places to visit', 'visit near me', 'near me']
        if any(keyword in message for keyword in nearest_place_keywords):
            if user_lat is None or user_lon is None:
                return Response({"reply": "Please share your location (latitude and longitude) to find nearby places."})

            try:
                user_lat = float(user_lat)
                user_lon = float(user_lon)
            except (ValueError, TypeError):
                return Response({"reply": "Invalid latitude or longitude values."}, status=status.HTTP_400_BAD_REQUEST)

            places = Place.objects.all()
            places_with_distance = []
            for place in places:
                try:
                    distance_km = haversine(user_lat, user_lon, place.latitude, place.longitude)
                    places_with_distance.append((distance_km, place))
                except Exception:
                    continue
            
            places_with_distance.sort(key=lambda x: x[0])
            nearest_places = places_with_distance[:5]

            if not nearest_places:
                reply = "Sorry, I couldn't find any nearby places right now."
            else:
                reply = "Here are some nearby places you can visit:\n"
                for i, (dist, place) in enumerate(nearest_places, 1):
                    category = place.category if place.category else "General"
                    reply += f"{i}. {place.name} ({category}) - {dist:.2f} km away\n"
                reply += "What kind of activity are you interested in? Food, adventure, relaxation?"
            return Response({"reply": reply})

        # FAQ fuzzy matching
        faqs = FAQ.objects.all()
        faq_questions = [faq.question.lower() for faq in faqs]
        matches = difflib.get_close_matches(message, faq_questions, n=1, cutoff=0.5)

        if matches:
            matched_question = matches[0]
            try:
                answer = faqs.get(question__iexact=matched_question).answer
                return Response({"reply": answer})
            except FAQ.DoesNotExist:
                # Defensive fallback
                pass

        # Fallback reply
        return Response({
            "reply": "Sorry, I couldn't understand your question. "
                     "You can ask me about nearest places or FAQs."
        })


class NearestPlacesAPIView(APIView):
    """
    API view to get nearest places given latitude and longitude.
    Returns top 5 closest places with name, category, and distance in km.
    """

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
