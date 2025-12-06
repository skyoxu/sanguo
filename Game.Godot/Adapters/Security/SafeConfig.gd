extends Node

func save_user(path: String, sections: Dictionary) -> int:
    if not path.begins_with("user://"):
        return -1
    if path.find("..") != -1:
        return -2
    var cfg := ConfigFile.new()
    for sec in sections.keys():
        var m: Dictionary = sections[sec]
        for k in m.keys():
            cfg.set_value(str(sec), str(k), m[k])
    return cfg.save(path)

