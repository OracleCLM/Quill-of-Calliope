"""Force real discord.py (site-packages) before tests/discord/ shadow is cached."""
import sys
import importlib

# Remove cached shadow if present
for key in list(sys.modules.keys()):
    if key == "discord" or key.startswith("discord."):
        del sys.modules[key]

# Remove tests/ from path so pytest doesn't re-discover tests/discord as 'discord'
_tests_path = str(__import__('pathlib').Path(__file__).parents[1])
sys.path = [p for p in sys.path if p != _tests_path]

# Add real discord site-packages to front of path
import site
sys.path.insert(0, next((p for p in site.getsitepackages() if "site-packages" in p), ""))

# Pre-import real discord so it wins
import importlib.util
spec = importlib.util.spec_from_file_location(
    "discord",
    "/home/nic/anaconda3/lib/python3.13/site-packages/discord/__init__.py",
)
_real_discord = importlib.util.module_from_spec(spec)
sys.modules["discord"] = _real_discord
spec.loader.exec_module(_real_discord)
