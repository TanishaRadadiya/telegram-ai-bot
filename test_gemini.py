import google.generativeai as genai

genai.configure(api_key="AIzaSyCjMRd_atXDs-YdMKaeDMeTq8VP4jQ78DM")

try:
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content("Hello!")
    print("✅ API Key is valid!")
    print("Response:", response.text)
except Exception as e:
    print("❌ API Key is invalid:", e)
