from cli import DumontCLI
import json

cli = DumontCLI()
commands = cli.build_command_tree()
for resource, actions in sorted(commands.items()):
    print(f"\nResource: {resource}")
    for action, info in sorted(actions.items()):
        print(f"  - {action}: {info['method']} {info['path']}")
