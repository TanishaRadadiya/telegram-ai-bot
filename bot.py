from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import pymongo
import google.generativeai as genai
import requests
import datetime
import os
import time

# Replace with your MongoDB connection string
client = pymongo.MongoClient("mongodb+srv://Tanisha:Tanisha214@cluster0.tpvdr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["telegram_bot"]
users_collection = db["users"]
chat_history_collection = db["chat_history"]
files_collection = db["files"]

# Replace with your Gemini API key
genai.configure(api_key="AIzaSyCM1kX0KwzYzK37A22VJ_nleXPd9XyOAbk")
model = genai.GenerativeModel('gemini-pro')

# Replace with your Telegram bot token
TELEGRAM_TOKEN = "7577203683:AAEVXnDdKn2C6E1q5MVPSxFV6F6DeCdhBAU"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_data = {
        "first_name": user.first_name,
        "username": user.username,
        "chat_id": user.id,
        "phone_number": None
    }
    users_collection.update_one({"chat_id": user.id}, {"$set": user_data}, upsert=True)
    await update.message.reply_text("Welcome! Please share your contact information.")

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    # Check if update contains contact data
    if not update.message.contact:
        print("⚠️ No contact data received!")
        await update.message.reply_text("❌ Error: No contact data received.")
        return

    phone_number = update.message.contact.phone_number
    
    # Debugging: Print the received phone number
    print(f"📞 Phone number received: {phone_number}")
    
    # Update MongoDB
    result = users_collection.update_one(
        {"chat_id": user.id},
        {"$set": {"phone_number": phone_number}},
        upsert=True
    )
    
    # Debugging: Print MongoDB update result
    print(f"📌 MongoDB update result: {result.modified_count} documents updated.")
    
    # Send confirmation message
    await update.message.reply_text("✅ Thank you! Your phone number has been saved.")


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
    await file.download_to_drive(file_path)
    max_retries = 3  # Number of retries
    retry_delay = 2  # Delay between retries (in seconds)

    for attempt in range(max_retries):
        try:
            # Attempt to generate a description using the Gemini API
            response = model.generate_content(f"Describe this image: {file_path}")
            
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