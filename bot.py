from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import pymongo
import google.generativeai as genai
import requests
import datetime
import os
import time
from dotenv import load_dotenv  # Import the load_dotenv function

# Load environment variables from .env file
load_dotenv()

# Get environment variables
MONGODB_URI = os.getenv("MONGODB_URI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# MongoDB connection
client = pymongo.MongoClient(MONGODB_URI)
db = client["telegram_bot"]
users_collection = db["users"]
chat_history_collection = db["chat_history"]
files_collection = db["files"]

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Rest of your code remains the same...
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_data = {
        "first_name": user.first_name,
        "username": user.username,
        "chat_id": user.id,
        "phone_number": None
    }
    users_collection.update_one({"chat_id": user.id}, {"$set": user_data}, upsert=True)
    await update.message.reply_text("Welcome! Please share your phone number using the contact button.")

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    phone_number = update.message.contact.phone_number
    
    # Debug: Print the phone number
    print(f"Phone number received: {phone_number}")
    
    # Update MongoDB
    result = users_collection.update_one(
        {"chat_id": user.id},
        {"$set": {"phone_number": phone_number}},
        upsert=True
    )
    
    # Debug: Print MongoDB update result
    print(f"MongoDB update result: {result.modified_count} documents updated.")
    
    # Send confirmation message
    await update.message.reply_text("Thank you! Your phone number has been saved.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    max_retries = 3  # Number of retries
    retry_delay = 2  # Delay between retries (in seconds)

    for attempt in range(max_retries):
        try:
            # Use a prompt to ensure the Gemini API generates meaningful responses
            prompt = f"You are a helpful assistant. The user asked: {user_input}. Please provide a helpful response."
            response = model.generate_content(prompt)
            
            # Save chat history to MongoDB
            chat_history = {
                "chat_id": update.message.from_user.id,
                "user_input": user_input,
                "bot_response": response.text,
                "timestamp": datetime.datetime.now()
            }
            chat_history_collection.insert_one(chat_history)
            
            # Send the response to the user
            await update.message.reply_text(response.text)
            return  # Exit the function if successful

        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                # If all retries fail, send an error message to the user
                await update.message.reply_text("Sorry, I'm having trouble processing your request. Please try again later.")
                print(f"Final error in handle_message: {e}")
            else:
                # Wait before retrying
                time.sleep(retry_delay)

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.photo[-1].get_file()
    file_path = f"downloads/{file.file_id}.jpg"
    
    # Ensure the downloads folder exists
    os.makedirs("downloads", exist_ok=True)
    
    # Download the image file
    await file.download_to_drive(file_path)
    
    # Read the image file as binary data
    with open(file_path, "rb") as image_file:
        image_data = image_file.read()
    
    max_retries = 3  # Number of retries
    retry_delay = 2  # Delay between retries (in seconds)

    for attempt in range(max_retries):
        try:
            # Use a detailed prompt for image analysis
            prompt = "Describe this image in detail, including the objects, people, colors, and any other relevant information."
            
            # Pass the image data directly to the Gemini API
            response = model.generate_content([prompt, image_data])
            
            # Save file metadata to MongoDB
            file_data = {
                "chat_id": update.message.from_user.id,
                "filename": file_path,
                "description": response.text,
                "timestamp": datetime.datetime.now()
            }
            files_collection.insert_one(file_data)
            
            # Send the description to the user
            await update.message.reply_text(response.text)
            return  # Exit the function if successful

        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                # If all retries fail, send an error message to the user
                await update.message.reply_text("Sorry, I'm having trouble processing your request. Please try again later.")
                print(f"Final error in handle_image: {e}")
            else:
                # Wait before retrying
                time.sleep(retry_delay)

async def web_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.split("/websearch ")[1]
    search_url = f"https://api.duckduckgo.com/?q={query}&format=json"
    
    try:
        response = requests.get(search_url)
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()
        
        if not data.get('Abstract'):
            await update.message.reply_text("No results found.")
            return
        
        max_retries = 3  # Number of retries
        retry_delay = 2  # Delay between retries (in seconds)

        for attempt in range(max_retries):
            try:
                # Attempt to generate a summary using the Gemini API
                summary = model.generate_content(f"Summarize this: {data['Abstract']}")
                
                # Send the summary and top links to the user
                await update.message.reply_text(f"Summary: {summary.text}\n\nTop Links:\n{data['RelatedTopics'][0]['FirstURL']}")
                return  # Exit the function if successful

            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    # If all retries fail, send an error message to the user
                    await update.message.reply_text("Sorry, I'm having trouble processing your request. Please try again later.")
                    print(f"Final error in web_search: {e}")
                else:
                    # Wait before retrying
                    time.sleep(retry_delay)

    except Exception as e:
        print(f"Error in web_search: {e}")
        await update.message.reply_text("An error occurred while performing the web search. Please try again later.")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    application.add_handler(CommandHandler("websearch", web_search))
    application.run_polling()

if __name__ == "__main__":
    main()