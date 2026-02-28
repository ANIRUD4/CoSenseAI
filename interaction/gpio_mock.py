from typing import Dict, Any
from interaction.action_executor import ActionExecutor

class MockGPIOAdapter(ActionExecutor):
    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        # Just simulate output
        print(f"[MOCK GPIO] Executing action: {action}")
        return {
            "status": "executed",
            "mode": "mock",
            "action": action
        }
