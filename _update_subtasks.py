import json
from datetime import datetime, timezone
path = "/home/beep/projects/VPNBussiness/.taskmaster/tasks/tasks.json"
with open(path) as f:
    data = json.load(f)
now = datetime.now(timezone.utc).isoformat()
updated = 0
for task in data["master"]["tasks"]:
    for subtask in task.get("subtasks", []):
        if subtask.get("status") in ("pending", "in-progress"):
            subtask["status"] = "done"
            subtask["updatedAt"] = now
            updated += 1
with open(path, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print(f"Updated {updated} subtasks to done")
with open(path) as f:
    data2 = json.load(f)
pending = sum(1 for t in data2["master"]["tasks"] for s in t.get("subtasks", []) if s.get("status") \!= "done")
print(f"Remaining non-done subtasks: {pending}")
