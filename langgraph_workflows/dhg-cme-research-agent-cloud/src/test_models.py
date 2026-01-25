import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("../.env")

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

print("Listing models...")
for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        print(f"Name: {m.name}")
