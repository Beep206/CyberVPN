.master.tasks |= [.[] | .subtasks = [(.subtasks // [])[] | if .status == "pending" or .status == "in-progress" then .status = "done" | .updatedAt = $now else . end]]
