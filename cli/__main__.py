"""
Dumont Cloud CLI - Main entry point

Usage:
    dumont                           # Show help
    dumont config setup              # Configure API key
    dumont spot monitor              # Market data
    dumont instances list            # List instances
    dumont api GET /api/v1/health    # Direct API call
"""
import argparse
import sys

# Import shared i18n module (must be before other local imports for proper translation)
from .i18n import _, get_current_language
_cli_language = get_current_language()

from .utils.api_client import APIClient
from .commands.config import ConfigManager, ConfigCommands, ensure_configured
from .commands.api import APICommands, SmartRouter
from .commands.base import CommandBuilder
from .commands.wizard import WizardCommands
from .commands.model import ModelCommands
from .commands.models import ModelsCommands


def generate_dynamic_help() -> str:
    """Generate help text dynamically from SmartRouter shortcuts"""
    import re
    lines = []

    # Config commands (static - not in SmartRouter)
    lines.append(_("Configuration:"))
    lines.append("  config setup                    " + _("Configure API key"))
    lines.append("  config show                     " + _("Show configuration"))
    lines.append("  config set-key <key>            " + _("Set API key"))
    lines.append("  config set-url <url>            " + _("Set API URL"))
    lines.append("")

    # Group shortcuts by category, merging singular/plural
    category_merge = {
        "instance": "instances",
        "job": "jobs",
        "snapshot": "snapshots",
    }

    groups = {}
    for key, (method, path) in SmartRouter.SHORTCUTS.items():
        category = key[0]
        # Merge singular into plural
        category = category_merge.get(category, category)

        if category not in groups:
            groups[category] = []
        cmd = " ".join(key)
        # Extract path params
        params = ""
        if "{" in path:
            params = " " + " ".join(f"<{p}>" for p in re.findall(r'\{([^}]+)\}', path))
        # Simplify path for display
        display_path = path.replace("/api/v1/", "").replace("/api/", "")
        groups[category].append((cmd, params, method, display_path))

    # Category display names and order
    category_order = [
        ("auth", _("Authentication")),
        ("health", _("System")),
        ("instances", _("Instances")),
        ("spot", _("Market (Spot)")),
        ("savings", _("Savings")),
        ("serverless", _("Serverless GPU")),
        ("warmpool", _("Warm Pool")),
        ("jobs", _("Jobs")),
        ("snapshots", _("Snapshots")),
        ("models", _("Models")),
        ("hibernation", _("Hibernation")),
        ("finetune", _("Fine-tune")),
    ]

    # Print categories in order
    for category, display_name in category_order:
        if category not in groups:
            continue

        lines.append(f"{display_name}:")
        for cmd, params, method, path in sorted(groups[category]):
            full_cmd = f"{cmd}{params}"
            lines.append(f"  {full_cmd:<35} {method} {path}")
        lines.append("")

    # API direct access
    lines.append(_("Direct API:"))
    lines.append("  api list                        " + _("List all endpoints"))
    lines.append("  api GET /path                   " + _("GET request"))
    lines.append("  api POST /path key=value        " + _("POST request"))
    lines.append("")

    # Wizard
    lines.append(_("Wizard:"))
    lines.append("  wizard deploy [gpu] [options]   " + _("Quick GPU deploy"))

    return "\n".join(lines)


def main():
    # Generate dynamic epilog
    dynamic_help = generate_dynamic_help()

    parser = argparse.ArgumentParser(
        prog="dumont",
        description=_("Dumont Cloud CLI - GPU Cloud Management"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dynamic_help
    )

    parser.add_argument(
        "--api-url",
        help=_("API URL (default: ~/.dumont/config.json or localhost:8000)")
    )

    parser.add_argument(
        "--api-key",
        help=_("API Key (default: ~/.dumont/config.json or DUMONT_API_KEY)")
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help=_("Debug mode")
    )

    parser.add_argument(
        "--language", "-l",
        choices=["en", "es"],
        default=_cli_language,
        help=_("Language for CLI output (default: en, or LANGUAGE env var)")
    )

    parser.add_argument("command", nargs="?", help=_("Command or resource"))
    parser.add_argument("subcommand", nargs="?", help=_("Subcommand or action"))
    parser.add_argument("args", nargs="*", help=_("Additional arguments"))

    args = parser.parse_args()

    # Handle config commands (don't require API key)
    if args.command == "config":
        config_cmd = ConfigCommands()

        if args.subcommand == "setup" or args.subcommand is None:
            config_cmd.setup(
                api_key=args.args[0] if args.args else None,
                api_url=args.api_url
            )
            return

        if args.subcommand == "show":
            config_cmd.show()
            return

        if args.subcommand == "set-key":
            if not args.args:
                print(_("❌ Usage: dumont config set-key <api_key>"))
                sys.exit(1)
            config_cmd.set_key(args.args[0])
            return

        if args.subcommand == "set-url":
            if not args.args:
                print(_("❌ Usage: dumont config set-url <url>"))
                sys.exit(1)
            config_cmd.set_url(args.args[0])
            return

        if args.subcommand == "clear":
            config_cmd.clear()
            return

        print(_("❌ Unknown subcommand: {subcommand}").format(subcommand=args.subcommand))
        print(_("Available: setup, show, set-key, set-url, clear"))
        sys.exit(1)

    # Handle help
    if args.command in (None, "help", "--help", "-h"):
        parser.print_help()
        return

    # Handle version
    if args.command in ("version", "--version", "-v"):
        print(_("Dumont Cloud CLI v1.0.0"))
        return

    # For other commands, ensure configured (will prompt if needed)
    try:
        config = ensure_configured()
    except SystemExit:
        return

    # Get API URL
    api_url = args.api_url or config.get_api_url()

    # Create API client
    api = APIClient(base_url=api_url)

    # Only use api_key from config if no JWT token is saved
    # JWT token from login takes priority
    if not api.token_manager.get():
        api_key = args.api_key or config.get_api_key()
        if api_key:
            api.token_manager.token = api_key  # Set in memory only, don't save to file

    # Handle direct API commands
    if args.command == "api":
        api_cmd = APICommands(api)
        all_args = [args.subcommand] if args.subcommand else []
        all_args.extend(args.args or [])
        api_cmd.execute(all_args)
        return

    # Handle wizard commands
    if args.command == "wizard":
        wizard = WizardCommands(api)
        if args.subcommand == "deploy" or args.subcommand is None:
            # Parse wizard args
            gpu_name = None
            speed = "fast"
            max_price = 2.0
            region = "global"

            for arg in args.args or []:
                if "=" in arg:
                    key, value = arg.split("=", 1)
                    if key == "gpu":
                        gpu_name = value
                    elif key == "speed":
                        speed = value
                    elif key == "price":
                        max_price = float(value)
                    elif key == "region":
                        region = value
                else:
                    if not gpu_name:
                        gpu_name = arg

            if args.subcommand is None:
                print(_("🧙 Wizard Deploy - Quick GPU Provisioning"))
                print("")
                print(_("Usage: dumont wizard deploy [gpu] [options]"))
                print("")
                print(_("Options:"))
                print(_("  gpu=<name>       GPU type (e.g., 'RTX 4090', 'A100')"))
                print(_("  speed=<mode>     fast (default), slow, ultrafast"))
                print(_("  price=<$>        Max price per hour (default: 2.0)"))
                print(_("  region=<name>    Region filter (default: global)"))
                return

            wizard.deploy(gpu_name=gpu_name, speed=speed, max_price=max_price, region=region)
            return

    # Handle model install
    if args.command == "model" and args.subcommand == "install":
        model = ModelCommands(api)
        if len(args.args or []) < 2:
            print(_("❌ Usage: dumont model install <instance_id> <model_id>"))
            sys.exit(1)
        model.install(args.args[0], args.args[1])
        return

    # Handle models commands
    if args.command == "models":
        models_cmd = ModelsCommands(api)

        if args.subcommand == "list" or args.subcommand is None:
            models_cmd.list()
            return

        if args.subcommand == "templates":
            models_cmd.templates()
            return

        if args.subcommand == "deploy":
            if len(args.args or []) < 2:
                print(_("❌ Usage: dumont models deploy <type> <model_id> [options]"))
                sys.exit(1)

            model_type = args.args[0]
            model_id = args.args[1]
            options = {}
            for arg in args.args[2:]:
                if "=" in arg:
                    key, value = arg.split("=", 1)
                    options[key] = value

            models_cmd.deploy(model_type, model_id, **options)
            return

        if args.subcommand in ("get", "stop", "delete", "logs"):
            if not args.args:
                print(_("❌ Usage: dumont models {subcommand} <deployment_id>").format(subcommand=args.subcommand))
                sys.exit(1)

            method = getattr(models_cmd, args.subcommand)
            method(args.args[0])
            return

    # Try smart routing for shortcuts
    router = SmartRouter(api)
    all_args = [args.command]
    if args.subcommand:
        all_args.append(args.subcommand)
    all_args.extend(args.args or [])

    if router.route(all_args):
        return

    # Fall back to command builder (OpenAPI discovery)
    builder = CommandBuilder(api)
    builder.execute(args.command, args.subcommand, args.args or [])


if __name__ == "__main__":
    main()
