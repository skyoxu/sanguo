extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

var _bus: Node
var _last_emitted_type := ""

func before() -> void:
    _bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    _bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(_bus))
    _bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event_emitted"))

func _on_domain_event_emitted(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
    _last_emitted_type = str(type)

func _hud() -> Node:
    var hud = preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
    add_child(auto_free(hud))
    await get_tree().process_frame
    return hud

# ACC:T9.2
# ACC:T22.2
func test_hud_core_interactions_are_wired() -> void:
    var hud = await _hud()
    var dice: Button = hud.get_node("TopBar/HBox/DiceButton")
    _last_emitted_type = ""
    dice.emit_signal("pressed")
    await get_tree().process_frame
    assert_str(_last_emitted_type).is_equal("ui.hud.dice.roll")

    _bus.PublishSimple("core.sanguo.game.turn.started", "ut", "{\"ActivePlayerId\":\"p1\",\"Year\":3,\"Month\":2,\"Day\":1}")
    await get_tree().process_frame
    _bus.PublishSimple("core.sanguo.dice.rolled", "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"Value\":6}")
    await get_tree().process_frame
    assert_str(dice.text).is_equal("Dice: 6")

func test_hud_has_core_status_nodes() -> void:
    var hud = await _hud()
    assert_object(hud.get_node_or_null("TopBar/HBox/DiceButton")).is_not_null()
    assert_object(hud.get_node_or_null("TopBar/HBox/ActivePlayerLabel")).is_not_null()
    assert_object(hud.get_node_or_null("TopBar/HBox/DateLabel")).is_not_null()
    assert_object(hud.get_node_or_null("TopBar/HBox/MoneyLabel")).is_not_null()

func test_hud_updates_on_score_event() -> void:
    var hud = await _hud()
    var score_label: Label = hud.get_node("TopBar/HBox/ScoreLabel")
    _bus.PublishSimple("core.score.updated", "ut", "{\"value\":42}")
    await get_tree().process_frame
    assert_str(score_label.text).is_equal("Score: 42")

func test_hud_updates_on_health_event() -> void:
    var hud = await _hud()
    var hp_label: Label = hud.get_node("TopBar/HBox/HealthLabel")
    _bus.PublishSimple("core.health.updated", "ut", "{\"value\":77}")
    await get_tree().process_frame
    assert_str(hp_label.text).is_equal("HP: 77")

func test_hud_updates_on_sanguo_turn_started_event() -> void:
    var hud = await _hud()
    var active_label: Label = hud.get_node("TopBar/HBox/ActivePlayerLabel")
    var date_label: Label = hud.get_node("TopBar/HBox/DateLabel")
    var money_label: Label = hud.get_node("TopBar/HBox/MoneyLabel")

    _bus.PublishSimple("core.sanguo.game.turn.started", "ut", "{\"ActivePlayerId\":\"p1\",\"Year\":3,\"Month\":2,\"Day\":1}")
    await get_tree().process_frame
    assert_str(active_label.text).is_equal("Player: p1")
    assert_str(date_label.text).is_equal("Date: 0003-02-01")

    _bus.PublishSimple("core.sanguo.player.state.changed", "ut", "{\"PlayerId\":\"p1\",\"Money\":123,\"PositionIndex\":0}")
    await get_tree().process_frame
    assert_str(money_label.text).is_equal("Money: 123")

func test_dice_button_emits_ui_roll_event() -> void:
    var hud = await _hud()
    var dice: Button = hud.get_node("TopBar/HBox/DiceButton")
    _last_emitted_type = ""
    dice.emit_signal("pressed")
    await get_tree().process_frame
    assert_str(_last_emitted_type).is_equal("ui.hud.dice.roll")

func test_hud_updates_on_sanguo_dice_rolled_event() -> void:
    var hud = await _hud()
    var dice: Button = hud.get_node("TopBar/HBox/DiceButton")

    _bus.PublishSimple("core.sanguo.game.turn.started", "ut", "{\"ActivePlayerId\":\"p1\",\"Year\":3,\"Month\":2,\"Day\":1}")
    await get_tree().process_frame

    _bus.PublishSimple("core.sanguo.dice.rolled", "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"Value\":6}")
    await get_tree().process_frame
    assert_str(dice.text).is_equal("Dice: 6")

    _bus.PublishSimple("core.sanguo.dice.rolled", "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p2\",\"Value\":1}")
    await get_tree().process_frame
    assert_str(dice.text).is_equal("Dice: 6")
