from google import genai

client = genai.Client(api_key="AIzaSyA8Qjhzw7pZzNUYFoAQMJpGPMhexwzk0gA")

for model in client.models.list():
    print(model.name)