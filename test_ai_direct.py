import sys
import os
import asyncio

# Setup path to include Backend
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

async def test_ai():
    print("🤖 Testing AIService with Direct REST API...")
    
    # Check if google.generativeai is even installed
    try:
        import google.generativeai
        print("⚠️ Warning: google-generativeai is still installed in this environment.")
    except ImportError:
        print("✅ google-generativeai is NOT installed. Testing pure REST implementation.")

    from app.services.ai_service import ai_service
    
    if not ai_service.api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment.")
        return

    test_message = "Hello JournalX AI! What is a Supply and Demand zone?"
    print(f"User: {test_message}")
    
    response = await ai_service.get_response(test_message)
    print(f"AI: {response}")
    
    if response and "Initialization Failed" not in response and "unavailable" not in response:
        print("✅ AI Service test PASSED!")
    else:
        print("❌ AI Service test FAILED!")

if __name__ == "__main__":
    asyncio.run(test_ai())
