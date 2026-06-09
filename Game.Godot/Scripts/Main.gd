extends Control

var _label: Label
var _score: int = 0
var _hp: int = 100

func _should_show_template_demo_overlay() -> bool:
    var ff = get_node_or_null("/root/FeatureFlags")
    if ff != null and ff.has_method("IsEnabled"):
        if ff.IsEnabled("demo_overlay"):
            return true

    if OS.has_environment("TEMPLATE_DEMO") and str(OS.get_environment("TEMPLATE_DEMO")).to_lower() == "1":
        return true

    return false

func _ready() -> void:
    print("[TEMPLATE_SMOKE_READY] Main scene initialized")

    var demo_root = get_node_or_null("SplitRoot/TopArea/VBox")
    if demo_root != null:
        demo_root.visible = _should_show_template_demo_overlay()

    var db = get_node_or_null("/root/SqlDb")
    if db != null:
        var ok = db.TryOpen("user://data/game.db")
        if not ok:
            print("[DB] open failed: ", str(db.LastError))
        else:
            print("[DB] opened at user://data/game.db")
    _label = get_node_or_null("SplitRoot/TopArea/VBox/Output")
    var publish_btn = get_node_or_null("SplitRoot/TopArea/VBox/PublishBtn")
    if publish_btn != null:
        publish_btn.pressed.connect(_on_publish)
    var save_load_btn = get_node_or_null("SplitRoot/TopArea/VBox/SaveLoadBtn")
    if save_load_btn != null:
        save_load_btn.pressed.connect(_on_save_load)
    var log_btn = get_node_or_null("SplitRoot/TopArea/VBox/LogBtn")
    if log_btn != null:
        log_btn.pressed.connect(_on_log)
    var add_score_btn = get_node_or_null("SplitRoot/TopArea/VBox/AddScoreBtn")
    if add_score_btn != null:
        add_score_btn.pressed.connect(_on_add_score)
    var lose_hp_btn = get_node_or_null("SplitRoot/TopArea/VBox/LoseHpBtn")
    if lose_hp_btn != null:
        lose_hp_btn.pressed.connect(_on_lose_hp)
    # Listen to UI menu events to start/quit game
    var bus = get_node_or_null("/root/EventBus")
    if bus != null:
        bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event"))

    if _is_smoke_exit_on_ready_enabled():
        var delay_sec := 2.0
        if OS.has_environment("GD_SMOKE_EXIT_DELAY_SEC"):
            var raw = str(OS.get_environment("GD_SMOKE_EXIT_DELAY_SEC")).strip_edges()
            if raw != "":
                delay_sec = float(raw)
        if delay_sec < 0.0:
            delay_sec = 0.0
        print("[SMOKE] exit-on-ready enabled; quitting scene tree after ", delay_sec, "s")
        await get_tree().create_timer(delay_sec).timeout
        get_tree().call_deferred("quit")

func _is_smoke_exit_on_ready_enabled() -> bool:
    if not OS.has_environment("GD_SMOKE_EXIT_ON_READY"):
        return false
    var v = str(OS.get_environment("GD_SMOKE_EXIT_ON_READY")).strip_edges().to_lower()
    return v == "1" or v == "true" or v == "yes"

func _exit_tree() -> void:
    var bus = get_node_or_null("/root/EventBus")
    if bus == null:
        return
    var callable := Callable(self, "_on_domain_event")
    if bus.is_connected("DomainEventEmitted", callable):
        bus.disconnect("DomainEventEmitted", callable)

func _on_publish() -> void:
    var bus = get_node_or_null("/root/EventBus")
    if bus == null:
        if _label != null:
            _label.text = "EventBus not found"
        return
    bus.PublishSimple("demo.event", "ui", "{\"msg\":\"hello\"}")
    if _label != null:
        _label.text = "Published demo.event"

func _on_save_load() -> void:
    var ds = get_node_or_null("/root/DataStore")
    if ds == null:
        if _label != null:
            _label.text = "DataStore not found"
        return
    var key = "demo_save"
    var json = "{\"ts\":" + str(Time.get_unix_time_from_system()) + "}"
    ds.SaveSync(key, json)
    var loaded = ds.LoadSync(key)
    if _label != null:
        _label.text = "Loaded: " + str(loaded)

func _on_log() -> void:
    var logger = get_node_or_null("/root/Logger")
    if logger == null:
        if _label != null:
            _label.text = "Logger not found"
        return
    logger.Info("Hello from Main.gd")
    if _label != null:
        _label.text = "Logged to console"

func _bus():
    return get_node_or_null("/root/EventBus")

func _on_add_score() -> void:
    _score += 10
    var demo = get_node_or_null("/root/Main/EngineDemo")
    if demo != null and demo.has_method("AddScore"):
        demo.AddScore(10)
    else:
        var bus = _bus()
        if bus != null:
            bus.PublishSimple("ui.demo.score.updated", "ui", "{\"value\":%d}" % _score)
    if _label != null:
        _label.text = "Score = %d" % _score

func _on_lose_hp() -> void:
    _hp = max(0, _hp - 5)
    var demo = get_node_or_null("/root/Main/EngineDemo")
    if demo != null and demo.has_method("ApplyDamage"):
        demo.ApplyDamage(5)
    else:
        var bus = _bus()
        if bus != null:
            bus.PublishSimple("ui.demo.health.updated", "ui", "{\"value\":%d}" % _hp)
    if _label != null:
        _label.text = "HP = %d" % _hp

func _on_domain_event(type: String, source: String, data_json: String, id: String, spec: String, ct: String, ts: String) -> void:
    if type == "ui.menu.start":
        var nav = get_node_or_null("/root/Main/ScreenNavigator")
        if nav != null and nav.has_method("SwitchTo"):
            var _use_demo := false
            var _ff = get_node_or_null("/root/FeatureFlags")
            if _ff != null and _ff.has_method("IsEnabled"):
                _use_demo = _ff.IsEnabled("demo_screens")
            elif OS.has_environment("TEMPLATE_DEMO") and str(OS.get_environment("TEMPLATE_DEMO")).to_lower() == "1":
                _use_demo = true
            if _use_demo:
                var ok = nav.SwitchTo("res://Game.Godot/Examples/Screens/DemoScreen.tscn")
                if ok:
                    return
            # Default gameplay uses the always-present Main scene (HUD + board view).
            # Avoid switching to placeholder screens that can block input.
    elif type == "ui.menu.settings":
        var sp = get_node_or_null("/root/Main/SettingsLayer/SettingsPanel")
        if sp != null and sp.has_method("ShowPanel"):
            sp.ShowPanel()
    elif type == "ui.menu.help":
        ToggleHelpTutorial()
    elif type == "ui.menu.quit":
        get_tree().quit()

func ToggleHelpTutorial() -> void:
    var nodes := get_tree().get_nodes_in_group("help_tutorial")
    if nodes == null or nodes.size() == 0:
        return
    var any_visible := false
    for n in nodes:
        if n is CanvasItem and n.visible:
            any_visible = true
            break
    var new_visible := not any_visible
    for n in nodes:
        if n is CanvasItem:
            n.visible = new_visible
