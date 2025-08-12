import { MapPin, MessageCircle, Star } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Hero Section */}
      <div className="container mx-auto px-6 py-16">
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">Your AI Travel Assistant</h1>
          <p className="text-xl text-gray-600 mb-8 leading-relaxed">
            Discover amazing places, get personalized recommendations, and plan your perfect trip with our intelligent
            chatbot companion.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3">
              Start Exploring
            </Button>
            <Button variant="outline" size="lg" className="px-8 py-3 bg-transparent">
              Learn More
            </Button>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="container mx-auto px-6 py-16">
        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          <Card className="p-6 text-center bg-white/80 backdrop-blur-sm border-0 shadow-lg">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <MapPin className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-3">Location-Based</h3>
            <p className="text-gray-600">
              Get recommendations for restaurants, attractions, and activities near your current location or any
              destination.
            </p>
          </Card>

          <Card className="p-6 text-center bg-white/80 backdrop-blur-sm border-0 shadow-lg">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <MessageCircle className="w-6 h-6 text-green-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-3">Smart Conversations</h3>
            <p className="text-gray-600">
              Have natural conversations about travel plans, ask questions, and get instant, helpful responses.
            </p>
          </Card>

          <Card className="p-6 text-center bg-white/80 backdrop-blur-sm border-0 shadow-lg">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <Star className="w-6 h-6 text-purple-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-3">Personalized</h3>
            <p className="text-gray-600">
              Receive tailored suggestions based on your preferences, budget, and travel style for the perfect
              experience.
            </p>
          </Card>
        </div>
      </div>

      {/* CTA Section */}
      <div className="container mx-auto px-6 py-16">
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 text-center max-w-2xl mx-auto shadow-lg">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Ready to Start Your Journey?</h2>
          <p className="text-gray-600 mb-6">
            Click the chat button in the bottom-right corner to begin exploring with your AI travel assistant.
          </p>
          <div className="flex items-center justify-center gap-2 text-blue-600">
            <MessageCircle className="w-5 h-5" />
            <span className="font-medium">Look for the chat icon →</span>
          </div>
        </div>
      </div>
    </main>
  )
}
