import os
from flask import Flask, jsonify, request
import json

# Assuming your run_all.py is in the same directory
from run_all import run_pipeline

app = Flask(__name__)

@app.route("/run-pipeline", methods=["POST"])
def run_pipeline_endpoint():
    try:
        # You can inspect the webhook payload here if needed
        # payload = request.get_json()
        
        # Run your main script
        run_pipeline()

        return jsonify({"status": "success", "message": "Pipeline triggered successfully"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))