from typing import Dict, Any

class ActionExecutor:
    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
