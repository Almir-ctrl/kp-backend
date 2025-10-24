from flask import Blueprint, jsonify, current_app

bp = Blueprint("models", __name__)


@bp.route("/models", methods=["GET"])
def list_models():
    models_cfg = current_app.config.get("MODELS", {})
    models_json = {}
    for model_name, config in models_cfg.items():
        models_json[model_name] = {
            **config,
            "file_types": list(config.get("file_types", [])),
            "available_models": list(config.get("available_models", [])),
        }

    return jsonify({"models": models_json, "message": "Available AI models"})


@bp.route("/models/<model_name>", methods=["GET"])
def get_model_info(model_name):
    cfg = current_app.config.get("MODELS", {})
    if model_name not in cfg:
        return jsonify({"error": f"Model {model_name} not found"}), 404

    config = cfg[model_name]
    config_json = {
        **config,
        "file_types": list(config.get("file_types", set())),
        "available_models": list(config.get("available_models", [])),
    }

    return jsonify({"model": model_name, "config": config_json})
