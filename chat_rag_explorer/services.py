import logging
from openai import OpenAI
from flask import current_app

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self):
        self.client = None

    def get_client(self):
        if not self.client:
            logger.debug("Initializing OpenAI client for OpenRouter")
            self.client = OpenAI(
                base_url=current_app.config["OPENROUTER_BASE_URL"],
                api_key=current_app.config["OPENROUTER_API_KEY"],
            )
        return self.client

    def chat_stream(self, message, model=None):
        client = self.get_client()
        target_model = model or current_app.config["DEFAULT_MODEL"]

        logger.info(f"Starting chat stream for model: {target_model}")
        logger.debug(f"User message: {message}")

        try:
            stream = client.chat.completions.create(
                model=target_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": message},
                ],
                stream=True,
            )

            chunk_count = 0
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    chunk_count += 1
                    yield content

            logger.info(f"Stream completed successfully with {chunk_count} chunks")

        except Exception as e:
            logger.error(f"Error in chat_stream: {str(e)}", exc_info=True)
            yield f"Error: {str(e)}"


chat_service = ChatService()
