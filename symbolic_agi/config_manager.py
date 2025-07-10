# symbolic_agi/config_manager.py
import re

class ConfigManager:
    def __init__(self, config_path="config.py"):
        self.config_path = config_path

    def read_config(self):
        with open(self.config_path, "r") as f:
            return f.read()

    def set_param(self, key, value):
        content = self.read_config()
        pattern = re.compile(rf"^{key}\s*=\s*.*$", re.MULTILINE)
        new_line = f"{key} = {repr(value)}"
        if pattern.search(content):
            content = pattern.sub(new_line, content)
        else:
            content += f"\n{new_line}\n"
        with open(self.config_path, "w") as f:
            f.write(content)

    def get_param(self, key, default=None):
        content = self.read_config()
        match = re.search(rf"^{key}\s*=\s*(.*)$", content, re.MULTILINE)
        if match:
            val = match.group(1).strip()
            try:
                return eval(val)
            except Exception:
                return val
        return default