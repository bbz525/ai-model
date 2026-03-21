import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL", "https://aihubmix.com/v1")

if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

client = OpenAI(api_key=api_key, base_url=base_url)

response = client.responses.create(
    model="gpt-5.4-pro",
    input="你是谁，你的模型版本？"
)

print(response.output_text )
