from openai import OpenAI
from flask import current_app


class ChatService:
    def __init__(self):
        self.client = None

    def get_client(self):
        if not self.client:
            self.client = OpenAI(
                base_url=current_app.config["OPENROUTER_BASE_URL"],
                api_key=current_app.config["OPENROUTER_API_KEY"],
            )
        return self.client

    def chat_stream(self, message, model=None):
        client = self.get_client()
        target_model = model or current_app.config["DEFAULT_MODEL"]

        try:
            stream = client.chat.completions.create(
                model=target_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": message},
                ],
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"Error: {str(e)}"


chat_service = ChatService()
