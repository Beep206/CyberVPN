import json
with open("/home/beep/projects/VPNBussiness/.taskmaster/tasks/tasks.json") as f:
    data = json.load(f)
tasks = data.get("master", data).get("tasks", data.get("tasks", []))
c = 0
for t in tasks:
    for s in t.get("subtasks", []):
        st = s.get("status", "")
        if st in ("pending", "in-progress"):
            c += 1
            print("Task %s.%s: [%s] %s" % (t["id"], s["id"], st, s["title"]))
print("")
print("Total pending/in-progress subtasks: %d" % c)
