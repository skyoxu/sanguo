extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

var _bus: Node
var _original_locale := ""

func before() -> void:
	if TranslationServer.has_method("get_locale"):
		_original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale("en")

	var existing := get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))

func after() -> void:
	if TranslationServer.has_method("set_locale") and _original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(_original_locale)

# acceptance: ACC:T54.3
# intent: HUD top bar shows identity + money; date remains visible for baseline gameplay HUD.
func test_task54_hud_shows_avatar_name_money_only() -> void:
	var hud = preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
	add_child(auto_free(hud))
	await get_tree().process_frame

	var avatar := hud.get_node_or_null("TopBar/TopStack/HBox/Avatar")
	var name_label := hud.get_node_or_null("TopBar/TopStack/HBox/ActivePlayerLabel")
	var money_label := hud.get_node_or_null("TopBar/TopStack/HBox/MoneyLabel")

	assert_object(avatar).is_not_null()
	assert_object(name_label).is_not_null()
	assert_object(money_label).is_not_null()

	assert_bool((avatar as CanvasItem).visible).is_true()
	assert_bool((name_label as CanvasItem).visible).is_true()
	assert_bool((money_label as CanvasItem).visible).is_true()

	var date_label := hud.get_node_or_null("TopBar/TopStack/HBox/DateLabel")
	var score_label := hud.get_node_or_null("TopBar/TopStack/HBox/ScoreLabel")
	var health_label := hud.get_node_or_null("TopBar/TopStack/HBox/HealthLabel")
	assert_object(date_label).is_not_null()
	assert_object(score_label).is_not_null()
	assert_object(health_label).is_not_null()
	assert_bool((date_label as CanvasItem).visible).is_true()
	assert_bool((score_label as CanvasItem).visible).is_false()
	assert_bool((health_label as CanvasItem).visible).is_false()

# acceptance: ACC:T54.4
func test_task54_hud_top_bar_has_expected_labels() -> void:
	var hud = preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
	add_child(auto_free(hud))
	await get_tree().process_frame

	var name_label := hud.get_node("TopBar/TopStack/HBox/ActivePlayerLabel") as Label
	var money_label := hud.get_node("TopBar/TopStack/HBox/MoneyLabel") as Label
	assert_str(name_label.text).contains("Player")
	assert_str(money_label.text).contains("Money")
