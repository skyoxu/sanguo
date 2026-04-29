extends RefCounted

func evaluate(issue_category: String) -> Dictionary:
	var is_crash := issue_category == "crash"
	return {
		"feedback": is_crash,
		"audit_only": not is_crash,
		"category": issue_category
	}
