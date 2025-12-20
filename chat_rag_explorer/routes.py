import logging
from flask import Blueprint, render_template, request, Response, stream_with_context
from chat_rag_explorer.services import chat_service

main_bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


@main_bp.route("/")
def index():
    logger.debug("Serving index page")
    return render_template("index.html")


@main_bp.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")
    model = data.get("model")

    logger.info(f"Received chat request. Model: {model}")

    if not user_message:
        logger.warning("Chat request received without message")
        return {"error": "Message is required"}, 400

    return Response(
        stream_with_context(chat_service.chat_stream(user_message, model)),
        mimetype="text/plain",
    )
