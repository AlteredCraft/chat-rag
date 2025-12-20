from flask import Blueprint, render_template, request, Response, stream_with_context
from chat_rag_explorer.services import chat_service

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")
    model = data.get("model")

    if not user_message:
        return {"error": "Message is required"}, 400

    return Response(
        stream_with_context(chat_service.chat_stream(user_message, model)),
        mimetype="text/plain",
    )
