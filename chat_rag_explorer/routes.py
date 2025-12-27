import logging
import time
import uuid
from flask import Blueprint, render_template, request, Response, stream_with_context, jsonify
from chat_rag_explorer.services import chat_service
from chat_rag_explorer.prompt_service import prompt_service

main_bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


def generate_request_id():
    """Generate a short unique request ID for log correlation."""
    return str(uuid.uuid4())[:8]


@main_bp.route("/")
def index():
    logger.debug("Serving index page")
    return render_template("index.html")


@main_bp.route("/settings")
def settings():
    logger.debug("Serving settings page")
    return render_template("settings.html")


@main_bp.route("/api/models")
def get_models():
    request_id = generate_request_id()
    start_time = time.time()
    logger.info(f"[{request_id}] GET /api/models - Fetching available models")

    try:
        models = chat_service.get_models(request_id)
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] GET /api/models - Returned {len(models)} models ({elapsed:.3f}s)")
        return jsonify({"data": models})
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] GET /api/models - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/prompts")
def get_prompts():
    request_id = generate_request_id()
    start_time = time.time()
    logger.info(f"[{request_id}] GET /api/prompts - Fetching available prompts")

    try:
        prompts = prompt_service.get_prompts(request_id)
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] GET /api/prompts - Returned {len(prompts)} prompts ({elapsed:.3f}s)")
        return jsonify({"data": prompts})
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] GET /api/prompts - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/prompts/<prompt_id>")
def get_prompt(prompt_id):
    request_id = generate_request_id()
    start_time = time.time()
    logger.info(f"[{request_id}] GET /api/prompts/{prompt_id} - Fetching prompt content")

    try:
        prompt = prompt_service.get_prompt_by_id(prompt_id, request_id)
        if prompt is None:
            logger.warning(f"[{request_id}] GET /api/prompts/{prompt_id} - Not found")
            return jsonify({"error": "Prompt not found"}), 404
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] GET /api/prompts/{prompt_id} - Success ({elapsed:.3f}s)")
        return jsonify({"data": prompt})
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] GET /api/prompts/{prompt_id} - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/chat", methods=["POST"])
def chat():
    request_id = generate_request_id()
    start_time = time.time()

    data = request.json
    messages = data.get("messages", [])
    model = data.get("model")
    temperature = data.get("temperature")
    top_p = data.get("top_p")

    # Calculate total message content length for logging
    total_content_length = sum(len(m.get("content", "")) for m in messages)

    logger.info(
        f"[{request_id}] POST /api/chat - Model: {model}, "
        f"Messages: {len(messages)}, Content length: {total_content_length} chars, "
        f"temperature: {temperature}, top_p: {top_p}"
    )
    logger.debug(f"[{request_id}] Message roles: {[m.get('role') for m in messages]}")

    if not messages:
        logger.warning(f"[{request_id}] POST /api/chat - Rejected: no messages provided")
        return {"error": "Messages are required"}, 400

    if not model:
        logger.warning(f"[{request_id}] POST /api/chat - No model specified, will use default")

    def stream_with_logging():
        """Wrapper to add logging around the stream."""
        try:
            chunk_count = 0
            for chunk in chat_service.chat_stream(messages, model, temperature, top_p, request_id):
                chunk_count += 1
                yield chunk
            elapsed = time.time() - start_time
            logger.info(f"[{request_id}] POST /api/chat - Stream completed ({elapsed:.3f}s, {chunk_count} chunks)")
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[{request_id}] POST /api/chat - Stream error after {elapsed:.3f}s: {str(e)}", exc_info=True)
            raise

    return Response(
        stream_with_context(stream_with_logging()),
        mimetype="text/plain",
    )
