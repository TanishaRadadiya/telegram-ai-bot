import google.generativeai as genai
from dotenv import load_dotenv  # Import the load_dotenv function
import os

# Load environment variables from .env file
load_dotenv()

# Get the API key from the environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure the Gemini API
genai.configure(api_key=GEMINI_API_KEY)

try:
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content("Hello!")
    print("✅ API Key is valid!")
    print("Response:", response.text)
except Exception as e:
    print("❌ API Key is invalid or an error occurred:", e)