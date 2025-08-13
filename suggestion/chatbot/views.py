from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from .models import Place, FAQ
from math import radians, cos, sin, asin, sqrt
import difflib
import re
import logging
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)

class GeoUtils:
    """Utility class for geographical calculations"""
    
    @staticmethod
    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate the great circle distance between two points on Earth"""
        try:
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1 
            dlon = lon2 - lon1 
            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
            c = 2 * asin(sqrt(a))
            r = 6371  # Earth's radius in kilometers
            return c * r
        except (ValueError, TypeError) as e:
            logger.error(f"Error calculating distance: {e}")
            return float('inf')

class ChatbotConfig:
    """Configuration class for chatbot intents, categories, and responses"""
    
    INTENTS = {
        "greeting": {
            "keywords": ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 
                        'hiya', 'howdy', 'greetings', 'sup', 'whatsup'],
            "response": "Hello! Welcome to our service. How can I help you today? 😊"
        },
        "thanks": {
            "keywords": ['thanks', 'thank you', 'thx', 'ty', 'appreciate it', 'cheers', 'much appreciated'],
            "response": "You're very welcome! If you have any other questions, feel free to ask."
        },
        "goodbye": {
            "keywords": ['bye', 'goodbye', 'see you', 'later', 'take care', 'farewell', 
                        'cya', 'see ya', 'until next time'],
            "response": "Goodbye! Have a wonderful day and safe travels! 👋"
        },
        "smalltalk": {
            "keywords": ['how are you', 'how is it going', 'hows it going', 'whats up', 
                        'how you doing', 'whats new'],
            "response": "I'm doing great, thanks for asking! I'm here and ready to help you discover amazing places. How about you?"
        },
        "help": {
            "keywords": ['help', 'assist me', 'can you help me', 'what can you do', 
                        'how does this work', 'commands', 'options'],
            "response": "I can help you with:\n• Finding nearby places by category\n• Getting places within specific time/distance\n• Mood-based recommendations\n• Answering FAQs\n• General travel assistance"
        },
        "yes": {
            "keywords": ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'absolutely', 'definitely'],
            "response": "Perfect! Let's continue. What would you like to explore?"
        },
        "no": {
            "keywords": ['no', 'nah', 'nope', 'not really', 'no thanks'],
            "response": "No problem at all! I'm here whenever you need assistance."
        }
    }

    CATEGORIES = {
        "park": ["park", "gardens", "green area", "picnic spot", "playground", "nature", 
                "outdoor", "green space", "botanical garden"],
        "museum": ["museum", "gallery", "exhibition", "art place", "history center", 
                  "cultural center", "heritage site", "art museum"],
        "restaurant": ["restaurant", "diner", "eatery", "cafe", "coffee shop", "bistro", 
                      "food place", "dining", "lunch", "dinner", "breakfast"],
        "shopping": ["shopping mall", "mall", "marketplace", "bazaar", "shops", "stores", 
                    "shopping center", "retail", "boutique"],
        "lake": ["lake", "pond", "reservoir", "waterbody", "beach", "waterfront", "river"],
        "adventure": ["adventure park", "amusement park", "funfair", "waterpark", 
                     "theme park", "rides", "thrilling", "exciting"],
        "relaxation": ["relaxation", "spa", "wellness", "meditation", "yoga", "peaceful", 
                      "tranquil", "zen"],
        "kids": ["kids", "children", "play area", "kid friendly", "family fun", "playground"],
        "family friendly": ["family friendly", "family trip", "family outing", "all ages"],
        "romantic": ["romantic", "date spot", "couples", "love spot", "intimate", "cozy"],
        "quiet": ["quiet", "peaceful", "calm", "serene", "silent", "tranquil"],
        "photography": ["photography", "photo spot", "instagrammable", "scenic view", 
                       "photogenic", "beautiful views"]
    }

    MOODS = {
        'romantic': 'romantic',
        'friends': 'family friendly',
        'family': 'family friendly',
        'photography': 'photography',
        'quiet': 'quiet',
        'adventure': 'adventure',
        'relax': 'relaxation',
        'peaceful': 'quiet'
    }

class MessageProcessor:
    """Handles message processing and intent detection"""
    
    @staticmethod
    def clean_message(message: str) -> str:
        """Clean and normalize the input message"""
        if not message:
            return ""
        message = str(message).strip().lower()
        message = re.sub(r'[^\w\s]', '', message)  # Remove punctuation
        message = re.sub(r'\s+', ' ', message)     # Collapse spaces
        return message

    @staticmethod
    def find_intent(message: str) -> Tuple[Optional[str], Optional[str]]:
        """Find the intent and response for a given message"""
        for intent, data in ChatbotConfig.INTENTS.items():
            for keyword in data['keywords']:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, message):
                    return intent, data['response']
        return None, None

    @staticmethod
    def extract_filters(message: str) -> Dict[str, Any]:
        """Extract time and distance filters from message"""
        filters = {}
        
        # Extract hours
        time_match = re.search(r'(\d+)\s*hour', message)
        if time_match:
            filters['hours'] = int(time_match.group(1))
        
        # Extract distance
        dist_patterns = [
            r'(?:within\s*)?(\d+)\s*km',
            r'(\d+)\s*km\s*distance',
            r'distance\s*(\d+)\s*km',
            r'(\d+)\s*kilometer'
        ]
        
        for pattern in dist_patterns:
            dist_match = re.search(pattern, message)
            if dist_match:
                filters['max_distance'] = float(dist_match.group(1))
                break
        
        return filters

class LocationValidator:
    """Handles location validation and processing"""
    
    @staticmethod
    def validate_location(lat: Any, lon: Any) -> Tuple[bool, Any]:
        """Validate latitude and longitude values"""
        if lat is None or lon is None:
            return False, Response({
                "type": "location_request", 
                "reply": "Please share your location (latitude and longitude) to get personalized recommendations."
            })
        
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            
            # Validate coordinate ranges
            if not (-90 <= lat_f <= 90) or not (-180 <= lon_f <= 180):
                return False, Response({
                    "type": "error", 
                    "reply": "Invalid coordinates. Latitude must be between -90 and 90, longitude between -180 and 180."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return True, (lat_f, lon_f)
        except (ValueError, TypeError):
            return False, Response({
                "type": "error", 
                "reply": "Invalid latitude or longitude values. Please provide numeric coordinates."
            }, status=status.HTTP_400_BAD_REQUEST)

class PlaceService:
    """Service class for place-related operations"""
    
    @staticmethod
    def get_places_by_category(user_lat: float, user_lon: float, category: str, limit: int = 5) -> List[Dict]:
        """Get places filtered by category and sorted by distance"""
        cache_key = f"places_category_{category}_{user_lat}_{user_lon}_{limit}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        places = Place.objects.filter(category__icontains=category)
        matched_places = []
        
        for place in places:
            try:
                dist_km = GeoUtils.haversine(user_lat, user_lon, place.latitude, place.longitude)
                matched_places.append({
                    "name": place.name,
                    "category": place.category or "General",
                    "distance_km": round(dist_km, 2),
                    "latitude": place.latitude,
                    "longitude": place.longitude,
                    "description": getattr(place, 'description', ''),
                    "rating": getattr(place, 'rating', None)
                })
            except Exception as e:
                logger.error(f"Error processing place {place.name}: {e}")
                continue
        
        matched_places.sort(key=lambda x: x['distance_km'])
        result = matched_places[:limit]
        
        # Cache for 10 minutes
        cache.set(cache_key, result, 600)
        return result

    @staticmethod
    def get_filtered_places(user_lat: float, user_lon: float, hours: Optional[int] = None, 
                           max_distance: Optional[float] = None, limit: int = 5) -> List[Dict]:
        """Get places filtered by time and distance constraints"""
        places = Place.objects.all()
        filtered_places = []
        
        for place in places:
            try:
                dist_km = GeoUtils.haversine(user_lat, user_lon, place.latitude, place.longitude)
                duration = getattr(place, 'average_duration', 1)
                
                # Apply filters
                if hours is not None and duration > hours:
                    continue
                if max_distance is not None and dist_km > max_distance:
                    continue
                
                filtered_places.append({
                    "name": place.name,
                    "category": place.category or "General",
                    "distance_km": round(dist_km, 2),
                    "duration_hours": duration,
                    "latitude": place.latitude,
                    "longitude": place.longitude,
                    "description": getattr(place, 'description', ''),
                    "rating": getattr(place, 'rating', None)
                })
            except Exception as e:
                logger.error(f"Error processing place {place.name}: {e}")
                continue
        
        filtered_places.sort(key=lambda x: x['distance_km'])
        return filtered_places[:limit]

class ChatbotMessageAPIView(APIView):
    """Main chatbot API view handling all message processing"""
    
    def post(self, request) -> Response:
        try:
            raw_message = request.data.get('message', '')
            user_lat = request.data.get('latitude')
            user_lon = request.data.get('longitude')
            
            if not raw_message:
                return Response({
                    "type": "error", 
                    "reply": "Please send a message to get started!"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            message = MessageProcessor.clean_message(raw_message)
            
            # 1. Check basic intents first
            intent, reply = MessageProcessor.find_intent(message)
            if intent:
                return Response({"type": intent, "reply": reply})
            
            # 2. Extract filters for time/distance based queries
            filters = MessageProcessor.extract_filters(message)
            
            if filters.get('hours') or filters.get('max_distance'):
                return self._handle_filtered_search(message, user_lat, user_lon, filters)
            
            # 3. Handle location-based queries
            if self._is_location_query(message):
                return self._handle_location_query(message, user_lat, user_lon)
            
            # 4. Category detection
            category_response = self._handle_category_query(message, user_lat, user_lon)
            if category_response:
                return category_response
            
            # 5. Mood detection
            mood_response = self._handle_mood_query(message, user_lat, user_lon)
            if mood_response:
                return mood_response
            
            # 6. Special features placeholders
            special_response = self._handle_special_queries(message)
            if special_response:
                return special_response
            
            # 7. FAQ matching
            faq_response = self._handle_faq_query(message)
            if faq_response:
                return faq_response
            
            # 8. Fallback response
            return self._get_fallback_response()
            
        except Exception as e:
            logger.error(f"Error in ChatbotMessageAPIView: {e}")
            return Response({
                "type": "error",
                "reply": "Sorry, I encountered an error. Please try again."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _is_location_query(self, message: str) -> bool:
        """Check if the message is asking for location-based recommendations"""
        location_keywords = ['nearest', 'nearby', 'closest', 'near me', 'nearby me', 
                           'suggest', 'visit', 'visiting', 'recommend', 'show me']
        return any(word in message for word in location_keywords)
    
    def _handle_filtered_search(self, message: str, user_lat: Any, user_lon: Any, filters: Dict) -> Response:
        """Handle search queries with time/distance filters"""
        valid, result = LocationValidator.validate_location(user_lat, user_lon)
        if not valid:
            return result
        user_lat, user_lon = result
        
        hours = filters.get('hours')
        max_distance = filters.get('max_distance')
        
        filtered_places = PlaceService.get_filtered_places(
            user_lat, user_lon, hours, max_distance
        )
        
        if not filtered_places:
            filter_text = []
            if hours:
                filter_text.append(f"{hours} hours")
            if max_distance:
                filter_text.append(f"{max_distance} km")
            
            return Response({
                "type": "multi_filter_places",
                "places": [],
                "reply": f"Sorry, no places found matching your criteria: {', '.join(filter_text)}. Try expanding your search range!"
            })
        
        reply_parts = []
        if hours:
            reply_parts.append(f"within {hours} hours")
        if max_distance:
            reply_parts.append(f"within {max_distance} km")
        
        reply_msg = f"Here are some great places {' and '.join(reply_parts)}:\n" + "\n".join(
            [f"🔹 {p['name']} ({p['category']}) - {p['distance_km']} km away, ~{p['duration_hours']}h visit"
             for i, p in enumerate(filtered_places[:5])]
        )
        
        return Response({
            "type": "multi_filter_places", 
            "places": filtered_places[:5], 
            "reply": reply_msg
        })
    
    def _handle_location_query(self, message: str, user_lat: Any, user_lon: Any) -> Response:
        """Handle general location-based queries"""
        valid, result = LocationValidator.validate_location(user_lat, user_lon)
        if not valid:
            return result
        user_lat, user_lon = result
        
        # Check for specific category in the location query
        requested_category = None
        for category, keywords in ChatbotConfig.CATEGORIES.items():
            if any(word in message for word in keywords):
                requested_category = category
                break
        
        if requested_category:
            matched_places = PlaceService.get_places_by_category(user_lat, user_lon, requested_category)
            if not matched_places:
                return Response({
                    "type": "category_places",
                    "places": [],
                    "reply": f"Sorry, no {requested_category} places found nearby. Try expanding your search area!"
                })
            
            reply_msg = f"Here are some fantastic {requested_category} places near you:\n" + "\n".join(
                [f"🔹 {p['name']} ({p['category']}) - {p['distance_km']} km away" 
                 for p in matched_places[:5]]
            )
            
            return Response({
                "type": "category_places",
                "places": matched_places[:5],
                "reply": reply_msg
            })
        else:
            # General nearest places query - check if there's any category hint
            category_hint = None
            for category, keywords in ChatbotConfig.CATEGORIES.items():
                if any(word in message for word in keywords):
                    category_hint = category
                    break
            return self._get_nearest_places(user_lat, user_lon, category_hint)
    
    def _get_nearest_places(self, user_lat: float, user_lon: float, category_hint: str = None) -> Response:
        """Get general nearest places without category filter"""
        places = Place.objects.all()
        places_with_distance = []
        
        for place in places:
            try:
                dist = GeoUtils.haversine(user_lat, user_lon, place.latitude, place.longitude)
                places_with_distance.append((dist, place))
            except Exception as e:
                logger.error(f"Error calculating distance for place {place.name}: {e}")
                continue
        
        places_with_distance.sort(key=lambda x: x[0])
        nearest = places_with_distance[:5]
        
        if not nearest:
            return Response({
                "type": "nearest_places", 
                "places": [], 
                "reply": "Sorry, I couldn't find any nearby places. Please check your location or try again later."
            })
        
        # Determine if we have a dominant category
        categories = [place.category or 'General' for dist, place in nearest]
        category_counts = {}
        for cat in categories:
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # If more than half are the same category, use that in the message
        most_common_category = max(category_counts, key=category_counts.get)
        if category_counts[most_common_category] >= 3 or category_hint:
            category_text = category_hint or most_common_category.lower()
            reply_msg = f"Here are some amazing {category_text} places near you:\n"
        else:
            reply_msg = "Here are some amazing places near you:\n"
            
        reply_msg += "\n".join(
            [f"🔹 {place.name} ({place.category or 'General'}) - {round(dist, 2)} km away"
             for i, (dist, place) in enumerate(nearest)]
        )
        
        places_data = [{
            "name": place.name,
            "category": place.category or "General",
            "distance_km": round(dist, 2),
            "latitude": place.latitude,
            "longitude": place.longitude,
            "description": getattr(place, 'description', ''),
            "rating": getattr(place, 'rating', None)
        } for dist, place in nearest]
        
        return Response({
            "type": "nearest_places",
            "places": places_data,
            "reply": reply_msg
        })
    
    def _handle_category_query(self, message: str, user_lat: Any, user_lon: Any) -> Optional[Response]:
        """Handle category-specific queries"""
        for category, keywords in ChatbotConfig.CATEGORIES.items():
            if any(word in message for word in keywords):
                valid, result = LocationValidator.validate_location(user_lat, user_lon)
                if not valid:
                    return result
                user_lat, user_lon = result
                
                matched_places = PlaceService.get_places_by_category(user_lat, user_lon, category)
                if not matched_places:
                    return Response({
                        "type": "category_places",
                        "places": [],
                        "reply": f"Sorry, no {category} places found near you. Would you like to try a different category?"
                    })
                
                reply_msg = f"Perfect! Here are some great {category} places for you:\n" + "\n".join(
                    [f"🔹 {p['name']} ({p['category']}) - {p['distance_km']} km away"
                     for p in matched_places[:5]]
                )
                
                return Response({
                    "type": "category_places",
                    "places": matched_places[:5],
                    "reply": reply_msg
                })
        return None
    
    def _handle_mood_query(self, message: str, user_lat: Any, user_lon: Any) -> Optional[Response]:
        """Handle mood-based queries"""
        for mood_key, mood_category in ChatbotConfig.MOODS.items():
            if mood_key in message:
                valid, result = LocationValidator.validate_location(user_lat, user_lon)
                if not valid:
                    return result
                user_lat, user_lon = result
                
                mood_places = PlaceService.get_places_by_category(user_lat, user_lon, mood_category)
                if not mood_places:
                    return Response({
                        "type": "mood_places", 
                        "places": [], 
                        "reply": f"Sorry, no places found perfect for {mood_key} mood near you. Try a different mood or expand your search area!"
                    })
                
                reply_msg = f"Great choice! Here are some places perfect for a {mood_key} experience:\n" + "\n".join(
                    [f"🔹 {p['name']} - {p['distance_km']} km away" for p in mood_places[:5]]
                )
                
                return Response({
                    "type": "mood_places", 
                    "places": mood_places[:5], 
                    "reply": reply_msg
                })
        return None
    
    def _handle_special_queries(self, message: str) -> Optional[Response]:
        """Handle special feature queries (opening hours, travel modes, etc.)"""
        if any(phrase in message for phrase in ['open now', 'open at', 'open today', 'opening hours']):
            return Response({
                "type": "open_hours", 
                "reply": "🕒 Opening hours feature is coming soon! We're working on real-time availability data."
            })
        
        if any(phrase in message for phrase in ['by car', 'by bike', 'by walk', 'walking distance', 'driving', 'cycling']):
            return Response({
                "type": "travel_mode", 
                "reply": "🚗 Travel mode filtering will be available soon! Currently showing straight-line distances."
            })
        
        return None
    
    def _handle_faq_query(self, message: str) -> Optional[Response]:
        """Handle FAQ matching using fuzzy string matching"""
        try:
            faqs = FAQ.objects.all()
            if not faqs.exists():
                return None
            
            faq_questions = [faq.question.lower() for faq in faqs]
            matches = difflib.get_close_matches(message, faq_questions, n=1, cutoff=0.5)
            
            if matches:
                matched_question = matches[0]
                try:
                    faq = faqs.get(question__iexact=matched_question)
                    return Response({
                        "type": "faq", 
                        "question": faq.question,
                        "reply": faq.answer
                    })
                except FAQ.DoesNotExist:
                    pass
        except Exception as e:
            logger.error(f"Error in FAQ matching: {e}")
        
        return None
    
    def _get_fallback_response(self) -> Response:
        """Return fallback response when no intent is matched"""
        fallback_reply = (
            "I'm not sure I understand that. Here are some things you can ask me:\n\n"
            "🔍 Find places: 'Show me nearby restaurants'\n"
            "⏰ Time-based: 'I have 3 hours to visit'\n" 
            "📍 Distance: 'Places within 5 km'\n"
            "🎯 Categories: 'Find parks near me'\n"
            "💭 Moods: 'Something romantic' or 'family friendly'\n"
            "❓ Help: Just type 'help' for more options!\n\n"
            "Feel free to ask me anything about places and recommendations!"
        )
        return Response({"type": "fallback", "reply": fallback_reply})


class NearestPlacesAPIView(APIView):
    """Dedicated API view for getting nearest places"""
    
    def post(self, request) -> Response:
        try:
            user_lat = request.data.get('latitude')
            user_lon = request.data.get('longitude')
            limit = min(int(request.data.get('limit', 5)), 20)  # Max 20 places
            
            valid, result = LocationValidator.validate_location(user_lat, user_lon)
            if not valid:
                return result
            user_lat, user_lon = result
            
            places = Place.objects.all()
            places_with_distance = []
            
            for place in places:
                try:
                    dist = GeoUtils.haversine(user_lat, user_lon, place.latitude, place.longitude)
                    places_with_distance.append((dist, place))
                except Exception as e:
                    logger.error(f"Error calculating distance for place {place.name}: {e}")
                    continue
            
            places_with_distance.sort(key=lambda x: x[0])
            nearest = places_with_distance[:limit]
            
            data = []
            for dist, place in nearest:
                data.append({
                    "name": place.name,
                    "category": place.category or "General",
                    "distance_km": round(dist, 2),
                    "latitude": place.latitude,
                    "longitude": place.longitude,
                    "description": getattr(place, 'description', ''),
                    "rating": getattr(place, 'rating', None)
                })
            
            return Response({
                "places": data,
                "total_found": len(data),
                "user_location": {"latitude": user_lat, "longitude": user_lon}
            })
            
        except Exception as e:
            logger.error(f"Error in NearestPlacesAPIView: {e}")
            return Response({
                "error": "An error occurred while fetching places"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)