import logging
import time
import uuid
from flask import Blueprint, render_template, request, Response, stream_with_context, jsonify
from chat_rag_explorer.services import chat_service
from chat_rag_explorer.prompt_service import prompt_service
from chat_rag_explorer.rag_config_service import rag_config_service

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


@main_bp.route("/api/prompts", methods=["POST"])
def create_prompt():
    request_id = generate_request_id()
    start_time = time.time()

    data = request.json
    prompt_id = data.get("id", "").strip()
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    content = data.get("content", "").strip()

    logger.info(f"[{request_id}] POST /api/prompts - Creating prompt: {prompt_id}")

    if not prompt_id:
        return jsonify({"error": "Prompt ID is required"}), 400
    if not title:
        return jsonify({"error": "Title is required"}), 400

    # Check if prompt ID is protected
    if prompt_service.is_protected(prompt_id):
        return jsonify({"error": "Cannot use this prompt ID"}), 403

    # Check if prompt already exists
    existing = prompt_service.get_prompt_by_id(prompt_id, request_id)
    if existing:
        return jsonify({"error": "A prompt with this ID already exists"}), 409

    try:
        prompt = prompt_service.save_prompt(prompt_id, title, description, content, request_id)
        if prompt is None:
            return jsonify({"error": "Failed to create prompt"}), 500
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] POST /api/prompts - Created ({elapsed:.3f}s)")
        return jsonify({"data": prompt}), 201
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] POST /api/prompts - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/prompts/<prompt_id>", methods=["PUT"])
def update_prompt(prompt_id):
    request_id = generate_request_id()
    start_time = time.time()

    data = request.json
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    content = data.get("content", "").strip()

    logger.info(f"[{request_id}] PUT /api/prompts/{prompt_id} - Updating prompt")

    if not title:
        return jsonify({"error": "Title is required"}), 400

    # Check if prompt is protected
    if prompt_service.is_protected(prompt_id):
        return jsonify({"error": "Cannot edit protected prompt"}), 403

    # Check if prompt exists
    existing = prompt_service.get_prompt_by_id(prompt_id, request_id)
    if not existing:
        return jsonify({"error": "Prompt not found"}), 404

    try:
        prompt = prompt_service.save_prompt(prompt_id, title, description, content, request_id)
        if prompt is None:
            return jsonify({"error": "Failed to update prompt"}), 500
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] PUT /api/prompts/{prompt_id} - Updated ({elapsed:.3f}s)")
        return jsonify({"data": prompt})
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] PUT /api/prompts/{prompt_id} - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/prompts/<prompt_id>", methods=["DELETE"])
def delete_prompt(prompt_id):
    request_id = generate_request_id()
    start_time = time.time()

    logger.info(f"[{request_id}] DELETE /api/prompts/{prompt_id} - Deleting prompt")

    # Check if prompt is protected
    if prompt_service.is_protected(prompt_id):
        return jsonify({"error": "Cannot delete protected prompt"}), 403

    # Check if prompt exists
    existing = prompt_service.get_prompt_by_id(prompt_id, request_id)
    if not existing:
        return jsonify({"error": "Prompt not found"}), 404

    try:
        success = prompt_service.delete_prompt(prompt_id, request_id)
        if not success:
            return jsonify({"error": "Failed to delete prompt"}), 500
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] DELETE /api/prompts/{prompt_id} - Deleted ({elapsed:.3f}s)")
        return jsonify({"success": True})
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] DELETE /api/prompts/{prompt_id} - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
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


# ==================== RAG Configuration Endpoints ====================


@main_bp.route("/api/rag/config")
def get_rag_config():
    """GET - Retrieve current RAG configuration."""
    request_id = generate_request_id()
    start_time = time.time()
    logger.info(f"[{request_id}] GET /api/rag/config - Fetching RAG configuration")

    try:
        config = rag_config_service.get_config(request_id)
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] GET /api/rag/config - Success ({elapsed:.3f}s)")
        return jsonify({"data": config})
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] GET /api/rag/config - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/rag/config", methods=["POST"])
def save_rag_config():
    """POST - Save RAG configuration."""
    request_id = generate_request_id()
    start_time = time.time()

    data = request.json
    logger.info(f"[{request_id}] POST /api/rag/config - Saving RAG configuration (mode: {data.get('mode')})")

    try:
        result = rag_config_service.save_config(data, request_id)
        elapsed = time.time() - start_time

        if 'error' in result:
            logger.warning(f"[{request_id}] POST /api/rag/config - Validation failed: {result['error']}")
            return jsonify(result), 400

        logger.info(f"[{request_id}] POST /api/rag/config - Saved ({elapsed:.3f}s)")
        return jsonify({"data": result['config']})
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] POST /api/rag/config - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/rag/validate-path", methods=["POST"])
def validate_rag_path():
    """POST - Validate a local ChromaDB path."""
    request_id = generate_request_id()
    start_time = time.time()

    data = request.json
    path = data.get("path", "")
    logger.info(f"[{request_id}] POST /api/rag/validate-path - Validating: {path}")

    try:
        result = rag_config_service.validate_local_path(path, request_id)
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] POST /api/rag/validate-path - Valid: {result['valid']} ({elapsed:.3f}s)")
        return jsonify(result)
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] POST /api/rag/validate-path - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"valid": False, "message": str(e)}), 500


@main_bp.route("/api/rag/test-connection", methods=["POST"])
def test_rag_connection():
    """POST - Test ChromaDB connection with provided config."""
    request_id = generate_request_id()
    start_time = time.time()

    data = request.json
    mode = data.get("mode", "local")
    logger.info(f"[{request_id}] POST /api/rag/test-connection - Testing connection (mode: {mode})")

    try:
        result = rag_config_service.test_connection(data, request_id)
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] POST /api/rag/test-connection - Success: {result['success']} ({elapsed:.3f}s)")
        return jsonify(result)
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] POST /api/rag/test-connection - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500


@main_bp.route("/api/rag/api-key-status")
def get_rag_api_key_status():
    """GET - Check if CHROMADB_API_KEY is configured."""
    request_id = generate_request_id()
    logger.debug(f"[{request_id}] GET /api/rag/api-key-status - Checking API key status")

    try:
        result = rag_config_service.get_api_key_status(request_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"[{request_id}] GET /api/rag/api-key-status - Failed: {str(e)}", exc_info=True)
        return jsonify({"configured": False, "masked": None}), 500
