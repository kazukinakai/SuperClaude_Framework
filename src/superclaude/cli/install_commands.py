"""
Command Installation

Installs SuperClaude slash commands to ~/.claude/commands/sc/ directory.
"""

import shutil
from pathlib import Path
from typing import List, Tuple


def install_commands(
    target_path: Path = None,
    force: bool = False
) -> Tuple[bool, str]:
    """
    Install all SuperClaude commands to Claude Code

    Args:
        target_path: Target installation directory (default: ~/.claude/commands/sc)
        force: Force reinstall if commands exist

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Default to ~/.claude/commands/sc to maintain /sc: namespace
    if target_path is None:
        target_path = Path.home() / ".claude" / "commands" / "sc"

    # Get command source directory
    command_source = _get_commands_source()

    if not command_source or not command_source.exists():
        return False, f"Command source directory not found: {command_source}"

    # Create target directory
    target_path.mkdir(parents=True, exist_ok=True)

    # Get all command files
    command_files = list(command_source.glob("*.md"))

    if not command_files:
        return False, f"No command files found in {command_source}"

    installed_commands = []
    skipped_commands = []
    failed_commands = []

    for command_file in command_files:
        target_file = target_path / command_file.name
        command_name = command_file.stem

        # Check if already exists
        if target_file.exists() and not force:
            skipped_commands.append(command_name)
            continue

        # Copy command file
        try:
            shutil.copy2(command_file, target_file)
            installed_commands.append(command_name)
        except Exception as e:
            failed_commands.append(f"{command_name}: {e}")

    # Build result message
    messages = []

    if installed_commands:
        messages.append(f"✅ Installed {len(installed_commands)} commands:")
        for cmd in installed_commands:
            messages.append(f"   - /{cmd}")

    if skipped_commands:
        messages.append(f"\n⚠️  Skipped {len(skipped_commands)} existing commands (use --force to reinstall):")
        for cmd in skipped_commands:
            messages.append(f"   - /{cmd}")

    if failed_commands:
        messages.append(f"\n❌ Failed to install {len(failed_commands)} commands:")
        for fail in failed_commands:
            messages.append(f"   - {fail}")

    if not installed_commands and not skipped_commands:
        return False, "No commands were installed"

    messages.append(f"\n📁 Installation directory: {target_path}")
    messages.append("\n💡 Tip: Restart Claude Code to use the new commands")

    success = len(failed_commands) == 0
    return success, "\n".join(messages)


def _get_commands_source() -> Path:
    """
    Get source directory for commands

    Commands are stored in:
        plugins/superclaude/commands/

    Returns:
        Path to commands source directory
    """
    # Get package root (src/superclaude/)
    package_root = Path(__file__).resolve().parent.parent

    # Check if running from source checkout
    # package_root = src/superclaude/
    # repo_root = src/superclaude/../../ = project root
    repo_root = package_root.parent.parent

    # Try plugins/superclaude/commands/ in project root
    commands_dir = repo_root / "plugins" / "superclaude" / "commands"

    if commands_dir.exists():
        return commands_dir

    # If not found, try relative to package (for installed package)
    # This would be in site-packages/superclaude/commands/
    alt_commands_dir = package_root / "commands"
    if alt_commands_dir.exists():
        return alt_commands_dir

    return commands_dir  # Return first candidate even if doesn't exist


def list_available_commands() -> List[str]:
    """
    List all available commands

    Returns:
        List of command names
    """
    command_source = _get_commands_source()

    if not command_source.exists():
        return []

    commands = []
    for file in command_source.glob("*.md"):
        if file.stem != "README":
            commands.append(file.stem)

    return sorted(commands)


def list_installed_commands() -> List[str]:
    """
    List installed commands in ~/.claude/commands/sc/

    Returns:
        List of installed command names
    """
    commands_dir = Path.home() / ".claude" / "commands" / "sc"

    if not commands_dir.exists():
        return []

    installed = []
    for file in commands_dir.glob("*.md"):
        if file.stem != "README":
            installed.append(file.stem)

    return sorted(installed)
