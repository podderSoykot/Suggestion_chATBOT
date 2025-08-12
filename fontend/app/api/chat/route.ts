import { type NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    // Parse JSON body
    const { message, latitude, longitude } = await request.json();

    // Validate message presence
    if (!message || typeof message !== "string" || message.trim() === "") {
      return NextResponse.json(
        { error: "Message is required" },
        { status: 400 }
      );
    }

    // Prepare payload for backend chatbot API
    const chatbotPayload: Record<string, unknown> = { message: message.trim() };

    if (
      latitude !== undefined &&
      longitude !== undefined &&
      !isNaN(Number(latitude)) &&
      !isNaN(Number(longitude))
    ) {
      chatbotPayload.latitude = Number(latitude);
      chatbotPayload.longitude = Number(longitude);
    }

    // Call your backend chatbot API
    const chatbotResponse = await fetch(
      "https://suggestion-chatbot.onrender.com/api/chatbot/message/",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(chatbotPayload),
      }
    );

    if (!chatbotResponse.ok) {
      const errorText = await chatbotResponse.text();
      console.error("Chatbot API error:", chatbotResponse.status, errorText);
      throw new Error("Failed to get response from chatbot API");
    }

    const data = await chatbotResponse.json();

    // Ensure the backend reply exists
    if (!data.reply) {
      return NextResponse.json(
        { error: "No reply received from chatbot backend" },
        { status: 502 }
      );
    }

    // Return the chatbot reply to frontend
    return NextResponse.json({ reply: data.reply });
  } catch (error) {
    console.error("Error in chat API:", error);
    return NextResponse.json(
      { error: "Failed to process message" },
      { status: 500 }
    );
  }
}
