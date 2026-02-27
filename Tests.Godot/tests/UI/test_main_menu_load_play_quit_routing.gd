extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const MAIN_MENU_SCENE := "res://Game.Godot/Scenes/UI/MainMenu.tscn"
const MAIN_MENU_SCRIPT := "res://Game.Godot/Scripts/UI/MainMenu.cs"

const EVT_START := "ui.menu.start"
const EVT_SETTINGS := "ui.menu.settings"
const EVT_QUIT := "ui.menu.quit"
const EVT_LOAD := "ui.menu.load"

var _bus: Node
var _events: Array[Dictionary] = []

func before() -> void:
    # Install a temporary EventBus under /root to mimic Autoload.
    var existing = get_node_or_null("/root/EventBus")
    if existing != null:
        existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
        existing.queue_free()

    _bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    _bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(_bus))
    _bus.connect("DomainEventEmitted", Callable(self, "_on_evt"))

func _on_evt(type, source, data_json, id, spec, ct, ts) -> void:
    _events.append({
        "type": str(type),
        "source": str(source),
        "data_json": str(data_json),
        "id": str(id),
        "spec": str(spec),
        "ct": str(ct),
        "ts": str(ts),
    })

func _create_menu() -> Node:
    var menu = preload(MAIN_MENU_SCENE).instantiate()
    add_child(auto_free(menu))
    return menu

func _event_types() -> Array:
    var types: Array[String] = []
    for e in _events:
        types.append(str(e.get("type", "")))
    return types

func _has_visible_load_ui_except_button(root: Node, btn_load: Node) -> bool:
    var queue = [root]
    while queue.size() > 0:
        var node = queue.pop_front()
        if node == btn_load:
            continue
        if node is Control:
            var c = node as Control
            var n = String(c.name).to_lower()
            if n.contains("load") and c.visible:
                return true
        for child in node.get_children():
            queue.append(child)
    return false

func _read_res_text(path: String) -> String:
    if not FileAccess.file_exists(path):
        return ""
    var f = FileAccess.open(path, FileAccess.READ)
    if f == null:
        return ""
    return f.get_as_text(true)

# ACC:T28.4
func test_load_action_is_distinct_from_play_and_quit_when_present() -> void:
    _events.clear()
    var menu = _create_menu()
    await get_tree().process_frame

    var btn_play = menu.get_node_or_null("MenuRow/MenuBox/BtnPlay")
    var btn_quit = menu.get_node_or_null("MenuRow/MenuBox/BtnQuit")
    var btn_load = menu.get_node_or_null("MenuRow/MenuBox/BtnLoad")
    assert_object(btn_play).is_not_null()
    assert_object(btn_quit).is_not_null()
    assert_object(btn_load).is_not_null()
    if btn_load == null:
        return

    _events.clear()
    btn_load.emit_signal("pressed")
    await get_tree().process_frame
    var types = _event_types()
    assert_bool(types.has(EVT_LOAD)).is_true()
    assert_bool(types.has(EVT_START)).is_false()
    assert_bool(types.has(EVT_QUIT)).is_false()
    assert_bool(types.has(EVT_SETTINGS)).is_false()
    var load_panel = menu.get_node_or_null("LoadPanel")
    assert_object(load_panel).is_not_null()
    if load_panel != null:
        assert_bool((load_panel as Control).visible).is_true()

# ACC:T28.5
func test_load_produces_observable_state_when_present() -> void:
    _events.clear()
    var menu = _create_menu()
    await get_tree().process_frame

    var btn_load = menu.get_node_or_null("MenuRow/MenuBox/BtnLoad")
    assert_object(btn_load).is_not_null()
    if btn_load == null:
        return

    _events.clear()
    btn_load.emit_signal("pressed")
    await get_tree().process_frame

    var types = _event_types()
    assert_bool(types.has(EVT_LOAD)).is_true()
    assert_bool(types.has(EVT_START)).is_false()
    assert_bool(types.has(EVT_QUIT)).is_false()
    assert_bool(types.has(EVT_SETTINGS)).is_false()
    var load_panel = menu.get_node_or_null("LoadPanel")
    assert_object(load_panel).is_not_null()
    if load_panel != null:
        assert_bool((load_panel as Control).visible).is_true()

# ACC:T28.6
func test_play_and_quit_semantics_are_not_confused_smoke() -> void:
    _events.clear()
    var menu = _create_menu()
    await get_tree().process_frame

    var btn_play = menu.get_node("MenuRow/MenuBox/BtnPlay")
    assert_object(btn_play).is_not_null()

    _events.clear()
    btn_play.emit_signal("pressed")
    await get_tree().process_frame
    var types = _event_types()
    assert_bool(types.has(EVT_START)).is_false()
    assert_bool(types.has(EVT_QUIT)).is_false()
    assert_bool(menu.visible).is_true()

    var config_panel = menu.get_node_or_null("ConfigCenter/NewGameConfig")
    assert_object(config_panel).is_not_null()
    if config_panel != null:
        assert_bool((config_panel as Control).visible).is_true()

    var btn_start = menu.get_node_or_null("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnStart")
    assert_object(btn_start).is_not_null()
    if btn_start != null:
        btn_start.emit_signal("pressed")
        await get_tree().process_frame

    var types_after_start = _event_types()
    assert_bool(types_after_start.has(EVT_START)).is_true()
    assert_bool(types_after_start.has(EVT_QUIT)).is_false()

    var src = _read_res_text(MAIN_MENU_SCRIPT)
    assert_str(src).contains(EVT_START)
    assert_str(src).contains(EVT_QUIT)
    assert_str(EVT_START).is_not_equal(EVT_QUIT)

    _events.clear()
    var menu2 = _create_menu()
    await get_tree().process_frame
    var btn_quit = menu2.get_node_or_null("MenuRow/MenuBox/BtnQuit")
    var btn_load2 = menu2.get_node_or_null("MenuRow/MenuBox/BtnLoad")
    assert_object(btn_quit).is_not_null()
    assert_object(btn_load2).is_not_null()
    if btn_quit == null or btn_load2 == null:
        return

    btn_quit.emit_signal("pressed")
    await get_tree().process_frame
    var types2 = _event_types()
    assert_bool(types2.has(EVT_QUIT)).is_true()
    assert_bool(types2.has(EVT_START)).is_false()
    assert_bool(types2.has(EVT_SETTINGS)).is_false()
    assert_bool(types2.has(EVT_LOAD)).is_false()
    assert_bool(_has_visible_load_ui_except_button(menu2, btn_load2)).is_false()

    # If a dedicated load event exists in the menu script, it must not alias start/quit.
    if src.contains(EVT_LOAD):
        assert_str(EVT_LOAD).is_not_equal(EVT_START)
        assert_str(EVT_LOAD).is_not_equal(EVT_QUIT)
        var i = src.find("private void OnQuitPressed")
        if i < 0:
            i = src.find("void OnQuitPressed")
        if i >= 0:
            var snippet = src.substr(i, min(400, src.length() - i))
            assert_bool(snippet.contains(EVT_START)).is_false()
            assert_bool(snippet.contains(EVT_LOAD)).is_false()
