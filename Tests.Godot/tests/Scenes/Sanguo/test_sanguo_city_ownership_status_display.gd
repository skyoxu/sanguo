extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# Task 23 - UI City Ownership Status Display
# Notes:
# - Keep assertions observable (Label/Texture/Style), not logs.

const EVENT_CITY_BOUGHT := "core.sanguo.city.bought"
const SCENE_PATH := "res://Game.Godot/Scenes/Sanguo/SanguoCityOwnershipStatusDisplay.tscn"
const STATUS_LABEL_NAME := "OwnershipStatusLabel"

const STATUS_NODE_NAME_CANDIDATES := [
    "OwnershipStatusLabel",
    "OwnershipStatus",
    "CityOwnershipStatusLabel",
    "CityOwnershipStatus"
]

const OWNERSHIP_SETTER_METHOD_CANDIDATES := [
    "set_city_ownership",
    "set_ownership",
    "set_owner_id",
    "apply_city_ownership",
    "apply_ownership",
    "update_ownership"
]

var _bus: Node


func before() -> void:
    var existing = get_node_or_null("/root/EventBus")
    if existing != null:
        existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
        existing.queue_free()

    _bus = load("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    _bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(_bus))


func _publish_city_bought(game_id: String, buyer_id: String, city_id: String, payload_json: String = "") -> void:
    var payload := payload_json
    if payload.is_empty():
        payload = "{\"GameId\":\"%s\",\"BuyerId\":\"%s\",\"CityId\":\"%s\"}" % [game_id, buyer_id, city_id]
    _bus.PublishSimple(EVENT_CITY_BOUGHT, "gdunit", payload)


func _instantiate_ownership_ui() -> Node:
    var res = load(SCENE_PATH)
    assert_object(res).is_not_null()

    var packed = res as PackedScene
    assert_object(packed).is_not_null()

    var node = packed.instantiate()
    assert_object(node).is_not_null()

    add_child(auto_free(node))
    await get_tree().process_frame
    return node


func _get_status_label(root: Node) -> Label:
    var found = root.find_child(STATUS_LABEL_NAME, true, false)
    assert_object(found).is_not_null()
    assert_bool(found is Label).is_true()
    return found as Label

func _find_status_display_node(root: Node) -> Node:
    var label = root.find_child(STATUS_LABEL_NAME, true, false)
    if label != null:
        return label

    for candidate_name in STATUS_NODE_NAME_CANDIDATES:
        var found = root.find_child(candidate_name, true, false)
        if found != null:
            return found

    # Fallback heuristic: find a UI node whose name implies ownership/status.
    var stack: Array = [root]
    while stack.size() > 0:
        var current = stack.pop_back()
        for child in current.get_children():
            if child == null:
                continue
            stack.append(child)
            var node := child as Node
            if node == null:
                continue
            var lower := String(node.name).to_lower()
            if lower.find("ownership") != -1 or lower.find("owner") != -1 or lower.find("status") != -1:
                if node is Label or node is RichTextLabel or node is TextureRect:
                    return node

    return null


func _has_property(obj: Object, property_name: String) -> bool:
    for p in obj.get_property_list():
        if p is Dictionary and p.has("name") and String(p["name"]) == property_name:
            return true
    return false


func _try_set_ownership(root: Node, owner_id: String) -> bool:
    for method_name in OWNERSHIP_SETTER_METHOD_CANDIDATES:
        if root.has_method(method_name):
            root.call(method_name, owner_id)
            return true
    if _has_property(root, "owner_id"):
        root.set("owner_id", owner_id)
        return true
    if _has_property(root, "OwnerId"):
        root.set("OwnerId", owner_id)
        return true
    return false


func _try_set_city_id(root: Node, city_id: String) -> bool:
    if _has_property(root, "city_id"):
        root.set("city_id", city_id)
        return true
    if _has_property(root, "CityId"):
        root.set("CityId", city_id)
        return true
    return false


func _read_display_fingerprint(status_node: Node) -> String:
    if status_node is Label:
        return "label:" + (status_node as Label).text
    if status_node is RichTextLabel:
        return "rich:" + (status_node as RichTextLabel).text
    if status_node is TextureRect:
        var tex = (status_node as TextureRect).texture
        if tex == null:
            return "texture:"
        return "texture:" + tex.resource_path
    if status_node is CanvasItem:
        return "modulate:" + str((status_node as CanvasItem).modulate)
    return ""


# ACC:T23.1
func test_ui_scene_can_be_instantiated_and_has_visible_ownership_element() -> void:
    var root = await _instantiate_ownership_ui()
    assert_object(root).is_not_null()
    var label := _get_status_label(root)
    assert_bool(label.visible).is_true()


# ACC:T23.2
func test_initial_render_matches_current_ownership_and_updates_when_changed() -> void:
    var root = await _instantiate_ownership_ui()
    assert_object(root).is_not_null()
    var label := _get_status_label(root)

    assert_bool(_try_set_ownership(root, "")).is_true()
    await get_tree().process_frame
    assert_str(label.text).is_equal("Unowned")

    assert_bool(_try_set_ownership(root, "p1")).is_true()
    await get_tree().process_frame
    assert_str(label.text).is_equal("Owner: p1")


# ACC:T23.3
func test_ui_shows_updated_ownership_on_next_refresh() -> void:
    var root = await _instantiate_ownership_ui()
    assert_object(root).is_not_null()
    var label := _get_status_label(root)

    assert_bool(_try_set_ownership(root, "p1")).is_true()
    await get_tree().process_frame
    assert_str(label.text).is_equal("Owner: p1")

    assert_bool(_try_set_ownership(root, "p2")).is_true()
    await get_tree().process_frame
    assert_str(label.text).is_equal("Owner: p2")


# ACC:T23.4
func test_ownership_status_is_assertable_via_observable_ui_output() -> void:
    var root = await _instantiate_ownership_ui()
    assert_object(root).is_not_null()
    var status_node = _find_status_display_node(root)
    assert_object(status_node).is_not_null()

    assert_bool(_try_set_ownership(root, "p1")).is_true()
    await get_tree().process_frame
    var fp = _read_display_fingerprint(status_node)

    assert_bool(fp.length() > 0).is_true()
    assert_bool(
        fp.begins_with("label:")
        or fp.begins_with("rich:")
        or fp.begins_with("texture:")
        or fp.begins_with("modulate:")
    ).is_true()


# ACC:T23.5
func test_display_differs_for_two_distinct_ownership_inputs() -> void:
    var root = await _instantiate_ownership_ui()
    assert_object(root).is_not_null()
    var label := _get_status_label(root)

    assert_bool(_try_set_ownership(root, "")).is_true()
    await get_tree().process_frame
    assert_str(label.text).is_equal("Unowned")

    assert_bool(_try_set_ownership(root, "p1")).is_true()
    await get_tree().process_frame
    assert_str(label.text).is_equal("Owner: p1")


# ACC:T23.6
func test_updates_display_when_city_bought_event_emitted_for_matching_city() -> void:
    var root = await _instantiate_ownership_ui()
    assert_object(root).is_not_null()
    var label := _get_status_label(root)

    assert_bool(_try_set_city_id(root, "c1")).is_true()
    assert_bool(_try_set_ownership(root, "")).is_true()
    await get_tree().process_frame
    assert_str(label.text).is_equal("Unowned")

    _publish_city_bought("g1", "p1", "c1")
    await get_tree().process_frame
    assert_str(label.text).is_equal("Owner: p1")

