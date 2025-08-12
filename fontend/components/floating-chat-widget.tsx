"use client";

import type React from "react";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import {
  Send,
  MapPin,
  Loader2,
  MessageCircle,
  X,
  Minimize2,
  Navigation,
  Maximize2,
  Minimize,
} from "lucide-react";

interface Message {
  id: string;
  content: string;
  sender: "user" | "bot";
  timestamp: Date;
  places?: Array<{
    name: string;
    address: string;
    rating: number;
    distance: number;
  }>;
}

type ChatSize = "small" | "medium" | "large" | "custom";

export function FloatingChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [chatSize, setChatSize] = useState<ChatSize>("medium");
  const [customDimensions, setCustomDimensions] = useState({
    width: 320,
    height: 384,
  });
  const [isResizing, setIsResizing] = useState(false);
  const [resizeStart, setResizeStart] = useState({
    x: 0,
    y: 0,
    width: 0,
    height: 0,
  });
  const chatRef = useRef<HTMLDivElement>(null);

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      content: "Hello! I'm your travel assistant. How can I help you today?",
      sender: "bot",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [userLocation, setUserLocation] = useState<{
    lat: number;
    lng: number;
  } | null>(null);
  const [locationStatus, setLocationStatus] = useState<
    "requesting" | "granted" | "denied" | "unavailable"
  >("requesting");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const getSizeClasses = (size: ChatSize) => {
    if (isResizing || size === "custom") {
      return "";
    }
    switch (size) {
      case "small":
        return "w-72 h-80";
      case "medium":
        return "w-80 h-96";
      case "large":
        return "w-96 h-[32rem]";
      default:
        return "w-80 h-96";
    }
  };

  const toggleSize = () => {
    setChatSize((prev) => {
      let newSize: ChatSize;
      switch (prev) {
        case "small":
          newSize = "medium";
          setCustomDimensions({ width: 320, height: 384 });
          break;
        case "medium":
          newSize = "large";
          setCustomDimensions({ width: 384, height: 512 });
          break;
        case "large":
          newSize = "small";
          setCustomDimensions({ width: 288, height: 320 });
          break;
        default:
          newSize = "medium";
          setCustomDimensions({ width: 320, height: 384 });
      }
      return newSize;
    });
  };

  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    setChatSize("custom");
    setResizeStart({
      x: e.clientX,
      y: e.clientY,
      width: customDimensions.width,
      height: customDimensions.height,
    });
  };

  const handleResizeMove = (e: MouseEvent) => {
    if (!isResizing) return;

    const deltaX = e.clientX - resizeStart.x;
    const deltaY = resizeStart.y - e.clientY; // Fixed: removed inversion for proper top-left dragging

    const newWidth = Math.max(250, Math.min(600, resizeStart.width + deltaX));
    const newHeight = Math.max(300, Math.min(700, resizeStart.height + deltaY));

    setCustomDimensions({ width: newWidth, height: newHeight });
  };

  const handleResizeEnd = () => {
    setIsResizing(false);
  };

  useEffect(() => {
    if (isResizing) {
      document.addEventListener("mousemove", handleResizeMove);
      document.addEventListener("mouseup", handleResizeEnd);
      document.body.style.cursor = "nw-resize";
      document.body.style.userSelect = "none";

      return () => {
        document.removeEventListener("mousemove", handleResizeMove);
        document.removeEventListener("mouseup", handleResizeEnd);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };
    }
  }, [isResizing, resizeStart]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    requestLocation();
  }, []);

  const requestLocation = () => {
    if (!navigator.geolocation) {
      setLocationStatus("unavailable");
      return;
    }

    setLocationStatus("requesting");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setUserLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        });
        setLocationStatus("granted");
      },
      (error) => {
        console.log("Location access denied:", error);
        setLocationStatus("denied");
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000, // 5 minutes
      }
    );
  };

  const isLocationQuery = (message: string) => {
    const locationKeywords = [
      "nearest",
      "nearby",
      "close",
      "around",
      "near me",
      "places",
      "restaurants",
      "hotels",
      "attractions",
    ];
    return locationKeywords.some((keyword) =>
      message.toLowerCase().includes(keyword)
    );
  };

  const sendMessage = async () => {
    if (!inputValue.trim()) return;

    const isLocationBasedQuery = isLocationQuery(inputValue);

    if (
      isLocationBasedQuery &&
      !userLocation &&
      locationStatus !== "requesting"
    ) {
      const locationPromptMessage: Message = {
        id: Date.now().toString(),
        content:
          "I need your location to find nearby places. Please click the location button below to share your location.",
        sender: "bot",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, locationPromptMessage]);
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      sender: "user",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);

    if (isLocationBasedQuery && userLocation) {
      const locationInfoMessage: Message = {
        id: (Date.now() + 0.5).toString(),
        content: `Using your current location (${userLocation.lat.toFixed(
          4
        )}, ${userLocation.lng.toFixed(4)}) to find nearby places...`,
        sender: "bot",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, locationInfoMessage]);
    }

    setInputValue("");
    setIsLoading(true);
    setIsTyping(true);

    try {
      const payload = {
        message: inputValue,
        ...(userLocation && {
          location: userLocation,
          latitude: userLocation.lat,
          longitude: userLocation.lng,
        }),
      };

      console.log("Sending to backend:", JSON.stringify(payload, null, 2));

      await new Promise((resolve) => setTimeout(resolve, 800));

      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      console.log("Full backend response:", JSON.stringify(data, null, 2));

      let botResponse = "";
      let places = [];

      if (data && typeof data === "object") {
        botResponse =
          data.response ||
          data.message ||
          data.reply ||
          data.text ||
          data.content ||
          "";
        places = data.places || data.locations || data.results || [];

        if (!botResponse) {
          const stringValues = Object.values(data).filter(
            (val) => typeof val === "string"
          );
          if (stringValues.length > 0) {
            botResponse = stringValues[0] as string;
          }
        }
      } else if (typeof data === "string") {
        botResponse = data;
      }

      if (!botResponse) {
        botResponse = `I received your message but the response format was unexpected. Raw response: ${JSON.stringify(
          data
        )}`;
        console.error("Unexpected response format:", data);
      }

      setTimeout(() => {
        const botMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: botResponse,
          sender: "bot",
          timestamp: new Date(),
          places: places,
        };

        setMessages((prev) => [...prev, botMessage]);
        setIsTyping(false);
      }, 500);
    } catch (error) {
      console.error("Error sending message:", error);
      setTimeout(() => {
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          content:
            "Sorry, I'm having trouble connecting to the server. Please check if your backend is running on http://127.0.0.1:8000",
          sender: "bot",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
        setIsTyping(false);
      }, 500);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      {/* Chat Button */}
      {!isOpen && (
        <Button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-blue-600 hover:bg-blue-700 shadow-lg hover:shadow-xl transition-all duration-300 z-50 hover:scale-110 animate-bounce"
          size="icon"
        >
          <MessageCircle className="w-6 h-6 text-white transition-transform duration-200 hover:rotate-12" />
        </Button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div
          ref={chatRef}
          className={`fixed bottom-6 right-6 ${getSizeClasses(
            chatSize
          )} bg-white rounded-lg shadow-2xl border border-gray-200 flex flex-col z-50 transition-all duration-500 ease-out animate-in slide-in-from-bottom-4 slide-in-from-right-4 fade-in ${
            isResizing ? "select-none" : ""
          }`}
          style={
            chatSize === "custom" || isResizing
              ? {
                  width: `${customDimensions.width}px`,
                  height: `${customDimensions.height}px`,
                }
              : {}
          }
        >
          <div
            className="absolute -top-2 -left-2 w-6 h-6 cursor-nw-resize opacity-60 hover:opacity-100 transition-opacity duration-200 z-10 group"
            onMouseDown={handleResizeStart}
          >
            <div className="w-full h-full bg-blue-600 rounded-full shadow-lg hover:bg-blue-700 transition-colors duration-200 flex items-center justify-center group-hover:scale-110 transform transition-transform">
              <div className="w-3 h-3 border-2 border-white rounded-full"></div>
            </div>
          </div>

          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-4 py-3 rounded-t-lg flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageCircle className="w-5 h-5 animate-pulse" />
              <h3 className="font-semibold text-sm">Travel Assistant</h3>
              {locationStatus === "granted" && (
                <MapPin className="w-3 h-3 text-green-300 animate-pulse" />
              )}
              {(chatSize === "custom" || isResizing) && (
                <span className="text-xs opacity-75">
                  {customDimensions.width}×{customDimensions.height}
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              <Button
                onClick={toggleSize}
                variant="ghost"
                size="icon"
                className="w-6 h-6 text-white hover:bg-blue-700 transition-all duration-200 hover:scale-110"
                title={`Resize (${chatSize})`}
              >
                {chatSize === "small" ? (
                  <Maximize2 className="w-4 h-4 transition-transform duration-200 hover:rotate-12" />
                ) : chatSize === "large" ? (
                  <Minimize className="w-4 h-4 transition-transform duration-200 hover:rotate-12" />
                ) : (
                  <Maximize2 className="w-4 h-4 transition-transform duration-200 hover:rotate-12" />
                )}
              </Button>
              <Button
                onClick={() => setIsOpen(false)}
                variant="ghost"
                size="icon"
                className="w-6 h-6 text-white hover:bg-blue-700 transition-all duration-200 hover:scale-110"
              >
                <Minimize2 className="w-4 h-4 transition-transform duration-200 hover:rotate-12" />
              </Button>
              <Button
                onClick={() => setIsOpen(false)}
                variant="ghost"
                size="icon"
                className="w-6 h-6 text-white hover:bg-red-500 transition-all duration-200 hover:scale-110"
              >
                <X className="w-4 h-4 transition-transform duration-200 hover:rotate-90" />
              </Button>
            </div>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-gradient-to-b from-gray-50 to-white">
            {messages.map((message, index) => (
              <div
                key={message.id}
                className={`flex ${
                  message.sender === "user" ? "justify-end" : "justify-start"
                } animate-in slide-in-from-bottom-2 fade-in duration-300`}
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <div
                  className={`max-w-[85%] px-3 py-2 rounded-lg text-sm transition-all duration-300 hover:scale-[1.02] ${
                    message.sender === "user"
                      ? "bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-br-sm shadow-md hover:shadow-lg"
                      : "bg-white text-gray-900 border border-gray-200 rounded-bl-sm shadow-sm hover:shadow-md hover:border-blue-200"
                  }`}
                >
                  <p className="leading-relaxed">{message.content}</p>

                  {/* Display places if available */}
                  {message.places && message.places.length > 0 && (
                    <div className="mt-2 space-y-2">
                      {message.places.slice(0, 2).map((place, placeIndex) => (
                        <Card
                          key={placeIndex}
                          className="p-2 bg-blue-50 border-blue-100 transition-all duration-200 hover:bg-blue-100 hover:scale-[1.02] animate-in slide-in-from-left-2 fade-in"
                          style={{ animationDelay: `${placeIndex * 100}ms` }}
                        >
                          <div className="flex items-start gap-2">
                            <MapPin className="w-3 h-3 mt-0.5 text-blue-600 animate-pulse" />
                            <div className="flex-1 min-w-0">
                              <h4 className="font-medium text-xs text-gray-900">
                                {place.name}
                              </h4>
                              <p className="text-xs text-gray-600 mt-0.5 truncate">
                                {place.address}
                              </p>
                              <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                                <span>★ {place.rating}</span>
                                <span>{place.distance}m</span>
                              </div>
                            </div>
                          </div>
                        </Card>
                      ))}
                      {message.places.length > 2 && (
                        <p className="text-xs text-gray-500 text-center animate-in fade-in duration-500">
                          +{message.places.length - 2} more places
                        </p>
                      )}
                    </div>
                  )}

                  <p className="text-xs opacity-60 mt-1">
                    {message.timestamp.toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
              </div>
            ))}

            {(isLoading || isTyping) && (
              <div className="flex justify-start animate-in slide-in-from-bottom-2 fade-in">
                <div className="bg-white border border-gray-200 px-3 py-2 rounded-lg rounded-bl-sm flex items-center gap-2 shadow-sm">
                  <Loader2 className="w-3 h-3 animate-spin text-blue-600" />
                  <div className="flex items-center gap-1">
                    <span className="text-xs text-gray-600">Thinking</span>
                    <div className="flex gap-1">
                      <div
                        className="w-1 h-1 bg-gray-400 rounded-full animate-bounce"
                        style={{ animationDelay: "0ms" }}
                      ></div>
                      <div
                        className="w-1 h-1 bg-gray-400 rounded-full animate-bounce"
                        style={{ animationDelay: "150ms" }}
                      ></div>
                      <div
                        className="w-1 h-1 bg-gray-400 rounded-full animate-bounce"
                        style={{ animationDelay: "300ms" }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-200 p-3 bg-white rounded-b-lg">
            {locationStatus === "denied" && (
              <div className="mb-2">
                <Button
                  onClick={requestLocation}
                  variant="outline"
                  size="sm"
                  className="w-full text-xs h-7 border-blue-200 text-blue-600 hover:bg-blue-50 bg-transparent transition-all duration-200 hover:scale-[1.02] hover:border-blue-300"
                >
                  <Navigation className="w-3 h-3 mr-1 animate-pulse" />
                  Enable Location for Nearby Places
                </Button>
              </div>
            )}

            <div className="flex gap-2">
              <Input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me anything..."
                className="flex-1 text-sm h-8 transition-all duration-200 focus:scale-[1.02] focus:shadow-md"
                disabled={isLoading}
              />
              <Button
                onClick={sendMessage}
                disabled={!inputValue.trim() || isLoading}
                size="icon"
                className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 h-8 w-8 transition-all duration-200 hover:scale-110 hover:shadow-lg disabled:hover:scale-100"
              >
                <Send className="w-3 h-3 transition-transform duration-200 hover:translate-x-0.5" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
