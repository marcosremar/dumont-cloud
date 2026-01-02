"""Model Deploy CLI commands
Deploy and manage ML models (LLM, Whisper, Diffusion, Embeddings) via API
"""
import json
import sys
import time

from ..i18n import _


class ModelsCommands:
    """Deploy and manage model endpoints"""

    def __init__(self, api_client):
        self.api = api_client

    def list(self):
        """List all deployed models"""
        print("\n" + _("📦 Deployed Models") + "\n")
        print("=" * 70)

        response = self.api.call("GET", "/api/v1/models/", silent=True)

        if not response:
            print(_("❌ Could not fetch models. Make sure you are logged in."))
            sys.exit(1)

        models = response.get("models", [])

        if not models:
            print("\n" + _("   No models deployed yet."))
            print("\n" + _("💡 Deploy a model:"))
            print("   dumont models deploy llm meta-llama/Llama-3.1-8B-Instruct")
            print("   dumont models deploy whisper openai/whisper-large-v3")
            print("   dumont models deploy image stabilityai/stable-diffusion-xl-base-1.0")
            return

        for model in models:
            status_emoji = {
                "running": "🟢",
                "deploying": "🔵",
                "downloading": "🔵",
                "starting": "🔵",
                "stopped": "⚫",
                "error": "🔴",
            }.get(model.get("status", "pending"), "⚪")

            print(f"\n{status_emoji} {model.get('name', model.get('model_id', 'Unknown'))}")
            print(_("   ID:     {id}").format(id=model.get('id')))
            print(_("   Model:  {model}").format(model=model.get('model_id')))
            print(_("   Type:   {type}").format(type=model.get('model_type')))
            print(_("   Status: {status} ({message})").format(status=model.get('status'), message=model.get('status_message', '')))

            if model.get("status") == "running":
                print(_("   URL:    {url}").format(url=model.get('endpoint_url')))
                if model.get("access_type") == "private" and model.get("api_key"):
                    print(_("   Key:    {key}...").format(key=model.get('api_key')[:25]))
                print(_("   Cost:   ${cost:.2f}/h").format(cost=model.get('dph_total', 0)))

            if model.get("status") in ["deploying", "downloading", "starting"]:
                print(_("   Progress: {progress:.0f}%").format(progress=model.get('progress', 0)))

        print("\n" + "=" * 70)

    def templates(self):
        """List available templates"""
        print("\n" + _("📋 Available Model Templates") + "\n")
        print("=" * 70)

        response = self.api.call("GET", "/api/v1/models/templates", silent=True)

        if not response:
            print(_("❌ Could not fetch templates."))
            sys.exit(1)

        templates = response.get("templates", [])

        for template in templates:
            type_emoji = {
                "llm": "🤖",
                "speech": "🎤",
                "image": "🎨",
                "embeddings": "📊",
            }.get(template.get("type", ""), "📦")

            print(f"\n{type_emoji} {template.get('name')}")
            print(_("   Type:    {type}").format(type=template.get('type')))
            print(_("   Runtime: {runtime}").format(runtime=template.get('runtime')))
            print(_("   Port:    {port}").format(port=template.get('default_port')))
            print(_("   GPU:     {memory}GB+ required").format(memory=template.get('gpu_memory_required')))
            print("\n" + _("   Popular models:"))
            for model in template.get("popular_models", [])[:3]:
                print(f"     - {model.get('id')} ({model.get('size')})")

        print("\n" + "=" * 70)

    def deploy(self, model_type: str, model_id: str, **kwargs):
        """Deploy a new model"""
        print("\n" + _("🚀 Deploying {type} model: {model}").format(type=model_type, model=model_id) + "\n")
        print("=" * 60)

        # Build payload
        payload = {
            "model_type": model_type,
            "model_id": model_id,
            "gpu_type": kwargs.get("gpu", "RTX 4090"),
            "num_gpus": int(kwargs.get("num_gpus", 1)),
            "max_price": float(kwargs.get("max_price", 2.0)),
            "access_type": kwargs.get("access", "private"),
            "port": int(kwargs.get("port", 8000)),
        }

        if kwargs.get("name"):
            payload["name"] = kwargs["name"]

        if kwargs.get("instance_id"):
            payload["instance_id"] = int(kwargs["instance_id"])

        response = self.api.call("POST", "/api/v1/models/deploy", data=payload, silent=True)

        if not response or not response.get("success"):
            error = response.get("detail", _("Unknown error")) if response else _("Failed to connect")
            print(_("❌ Deploy failed: {error}").format(error=error))
            sys.exit(1)

        deployment_id = response.get("deployment_id")
        print(_("✅ Deployment started!"))
        print(_("   ID: {id}").format(id=deployment_id))
        print(_("   Estimated time: ~{minutes} minutes").format(minutes=response.get('estimated_time_seconds', 180) // 60))

        # Wait for deployment
        if kwargs.get("wait", True):
            print("\n" + _("⏳ Waiting for deployment to complete..."))
            self._wait_for_deployment(deployment_id)

        return deployment_id

    def _wait_for_deployment(self, deployment_id: str, timeout: int = 600):
        """Wait for deployment to complete"""
        start_time = time.time()
        last_progress = -1

        while time.time() - start_time < timeout:
            response = self.api.call("GET", f"/api/v1/models/{deployment_id}", silent=True)

            if not response:
                print(_("   ⚠ Could not check status"))
                time.sleep(5)
                continue

            status = response.get("status")
            progress = response.get("progress", 0)
            message = response.get("status_message", "")

            # Print progress if changed
            if progress != last_progress:
                bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
                print(f"\r   [{bar}] {progress:.0f}% - {message}", end="", flush=True)
                last_progress = progress

            if status == "running":
                print("\n\n" + _("✅ Deployment complete!"))
                print(_("   Endpoint: {url}").format(url=response.get('endpoint_url')))
                if response.get("access_type") == "private" and response.get("api_key"):
                    print(_("   API Key:  {key}").format(key=response.get('api_key')))
                print(_("   Cost:     ${cost:.2f}/h").format(cost=response.get('dph_total', 0)))
                return True

            if status == "error":
                print("\n\n" + _("❌ Deployment failed: {message}").format(message=message))
                return False

            time.sleep(5)

        print("\n\n" + _("⚠ Timeout waiting for deployment"))
        return False

    def get(self, deployment_id: str):
        """Get deployment details"""
        response = self.api.call("GET", f"/api/v1/models/{deployment_id}", silent=True)

        if not response:
            print(_("❌ Deployment {id} not found").format(id=deployment_id))
            sys.exit(1)

        print("\n" + _("📦 Deployment Details") + "\n")
        print("=" * 60)
        print(json.dumps(response, indent=2))

    def stop(self, deployment_id: str, force: bool = False):
        """Stop a running deployment"""
        print("\n" + _("⏹️ Stopping deployment {id}...").format(id=deployment_id))

        response = self.api.call(
            "POST",
            f"/api/v1/models/{deployment_id}/stop",
            data={"force": force},
            silent=True
        )

        if not response:
            print(_("❌ Failed to stop deployment"))
            sys.exit(1)

        print(_("✅ Deployment stopped"))

    def delete(self, deployment_id: str):
        """Delete a deployment"""
        print("\n" + _("🗑️ Deleting deployment {id}...").format(id=deployment_id))

        response = self.api.call(
            "DELETE",
            f"/api/v1/models/{deployment_id}",
            silent=True
        )

        # DELETE returns 204 No Content, so response may be empty
        print(_("✅ Deployment deleted"))

    def logs(self, deployment_id: str):
        """Get deployment logs"""
        response = self.api.call("GET", f"/api/v1/models/{deployment_id}/logs", silent=True)

        if not response:
            print(_("❌ Could not fetch logs for {id}").format(id=deployment_id))
            sys.exit(1)

        print("\n" + _("📋 Logs for {id}").format(id=deployment_id) + "\n")
        print("=" * 60)
        print(response.get("logs", _("No logs available")))
