import pymongo

try:
    client = pymongo.MongoClient("mongodb+srv://Tanisha:Tanisha214@cluster0.tpvdr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    db = client["telegram_bot"]
    
    print("✅ MongoDB Connection Successful!")
    print("Databases:", client.list_database_names())
    print("Collections:", db.list_collection_names())

except Exception as e:
    print("❌ MongoDB Connection Failed:", e)
