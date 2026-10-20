
import json

from ai_tools import get_inventory_discrepancies

result = get_inventory_discrepancies()

print(json.dumps(result, indent=2))
