from google import genai

client = genai.Client(api_key="AIzaSyBMeRfaru2ZSsf67A-40hfngFt-jx67PbI")

response = client.models.generate_content(
    model="gemini-2.5-flash", contents="Explain how AI works in a few words"
)
print(response.text)