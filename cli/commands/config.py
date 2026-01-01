"""Configuration commands - API key and settings management"""
import os
import json
from pathlib import Path
from typing import Optional

from ..i18n import _


# Config file location
CONFIG_DIR = Path.home() / ".dumont"
CONFIG_FILE = CONFIG_DIR / "config.json"


class ConfigManager:
    """Manages CLI configuration including API key"""

    def __init__(self):
        self.config_dir = CONFIG_DIR
        self.config_file = CONFIG_FILE
        self._config = None

    def _ensure_dir(self):
        """Ensure config directory exists"""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        """Load configuration from file"""
        if self._config is not None:
            return self._config

        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._config = {}
        else:
            self._config = {}

        return self._config

    def save(self, config: dict):
        """Save configuration to file"""
        self._ensure_dir()
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)
        self._config = config
        # Secure file permissions
        os.chmod(self.config_file, 0o600)

    def get(self, key: str, default=None):
        """Get a config value"""
        return self.load().get(key, default)

    def set(self, key: str, value):
        """Set a config value"""
        config = self.load()
        config[key] = value
        self.save(config)

    def get_api_url(self) -> str:
        """Get API URL from config or environment"""
        return (
            os.environ.get("DUMONT_API_URL") or
            self.get("api_url") or
            "http://localhost:8000"
        )

    def get_api_key(self) -> Optional[str]:
        """Get API key from config or environment"""
        return (
            os.environ.get("DUMONT_API_KEY") or
            self.get("api_key")
        )

    def is_configured(self) -> bool:
        """Check if CLI is configured with API key"""
        return self.get_api_key() is not None


class ConfigCommands:
    """Commands for managing CLI configuration"""

    def __init__(self):
        self.manager = ConfigManager()

    def setup(self, api_key: str = None, api_url: str = None):
        """Interactive setup or direct configuration"""
        print(_("🔧 Dumont Cloud CLI Setup"))
        print("=" * 40)

        config = self.manager.load()

        # API URL
        if api_url:
            config["api_url"] = api_url
        else:
            current_url = self.manager.get_api_url()
            print("\n" + _("Current API URL: {url}").format(url=current_url))
            new_url = input(_("New URL (Enter to keep): ")).strip()
            if new_url:
                config["api_url"] = new_url

        # API Key
        if api_key:
            config["api_key"] = api_key
        else:
            current_key = self.manager.get_api_key()
            if current_key:
                masked = current_key[:8] + "..." + current_key[-4:] if len(current_key) > 12 else "***"
                print("\n" + _("Current API Key: {key}").format(key=masked))
            else:
                print("\n" + _("No API Key configured."))

            print("\n" + _("To get your API Key:"))
            print(_("  1. Go to https://cloud.dumont.ai/settings"))
            print(_("  2. Click 'Generate API Key'"))
            print(_("  3. Copy the generated key"))
            print()

            new_key = input(_("API Key (Enter to keep): ")).strip()
            if new_key:
                config["api_key"] = new_key

        self.manager.save(config)
        print("\n" + _("✅ Configuration saved to ~/.dumont/config.json"))

    def show(self):
        """Show current configuration"""
        print(_("📋 Current Configuration"))
        print("=" * 40)

        api_url = self.manager.get_api_url()
        api_key = self.manager.get_api_key()

        print("\n" + _("API URL: {url}").format(url=api_url))

        if api_key:
            masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
            print(_("API Key: {key}").format(key=masked))
        else:
            print(_("API Key: (not configured)"))

        print("\n" + _("File: {file}").format(file=self.manager.config_file))

        if self.manager.config_file.exists():
            print(_("Status: ✅ Configured"))
        else:
            print(_("Status: ❌ Not configured"))
            print("\n" + _("Run: dumont config setup"))

    def set_key(self, api_key: str):
        """Set API key directly"""
        self.manager.set("api_key", api_key)
        print(_("✅ API Key saved!"))

    def set_url(self, api_url: str):
        """Set API URL directly"""
        self.manager.set("api_url", api_url)
        print(_("✅ API URL configured: {url}").format(url=api_url))

    def clear(self):
        """Clear all configuration"""
        if self.manager.config_file.exists():
            self.manager.config_file.unlink()
            print(_("✅ Configuration removed"))
        else:
            print(_("ℹ️ No configuration to remove"))


def get_config_manager() -> ConfigManager:
    """Get config manager instance"""
    return ConfigManager()


def ensure_configured() -> ConfigManager:
    """Ensure CLI is configured, prompt for setup if not"""
    manager = ConfigManager()

    if not manager.is_configured():
        print(_("⚠️  CLI not configured!"))
        print()
        print(_("To use the Dumont CLI, you need to configure your API Key."))
        print()

        response = input(_("Do you want to configure now? [Y/n]: ")).strip().lower()
        if response in ("", "s", "sim", "y", "yes"):
            cmd = ConfigCommands()
            cmd.setup()
            print()
        else:
            print("\n" + _("You can configure later with:"))
            print("  dumont config setup")
            print("\n" + _("Or set the environment variable:"))
            print("  export DUMONT_API_KEY=your_key_here")
            print()
            raise SystemExit(1)

    return manager
