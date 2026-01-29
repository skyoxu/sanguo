extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TYPE_LOOT_GRANTED = "core.sanguo.loot.granted"
const EVENT_TYPE_RELIC_APPLIED = "core.sanguo.relic.applied"
const LOCALE_ZH = "zh"

var _bus: Node

func before() -> void:
	var existing = get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))

func _hud() -> Node:
	var hud = preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
	add_child(auto_free(hud))
	await get_tree().process_frame
	return hud

func _event_log_messages(hud: Node) -> Array:
	var panel: Control = hud.get_node("EventLogPanel")
	var list: ItemList = panel.get_node("Margin/VBox/EventList")
	var items: Array = []
	for index in range(list.item_count):
		items.append(str(list.get_item_text(index)))
	return items

func _event_log_details(hud: Node) -> String:
	var panel: Control = hud.get_node("EventLogPanel")
	var details: Label = panel.get_node("Margin/VBox/Details/Scroll/DetailsText")
	return str(details.text)

func _try_translate(key: String) -> String:
	if TranslationServer.has_method("translate"):
		var translated = String(TranslationServer.translate(key))
		if translated.strip_edges().length() > 0 and translated != key:
			return translated
	return ""

func _require_translation(key: String) -> String:
	var translated := _try_translate(key)
	assert_bool(translated.strip_edges().length() > 0).is_true()
	return translated

func _normalize_token(token: String) -> String:
	var result := ""
	for i in range(token.length()):
		var ch := token[i]
		if ch == "-" or ch == " ":
			if not result.ends_with("_"):
				result += "_"
		elif ch >= "A" and ch <= "Z":
			if result.length() > 0 and not result.ends_with("_"):
				result += "_"
			result += String(ch).to_lower()
		else:
			result += String(ch).to_lower()
	return result

func _translate_token(category: String, token: String) -> String:
	var normalized := _normalize_token(token)
	var key := "ui.hud.event.shared.detail.%s.%s" % [category, normalized]
	return _require_translation(key)

func _set_locale(locale: String) -> String:
	var original := ""
	if TranslationServer.has_method("get_locale"):
		original = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale") and locale.strip_edges().length() > 0:
		TranslationServer.set_locale(locale)
	return original

func _restore_locale(original: String) -> void:
	if TranslationServer.has_method("set_locale") and original.strip_edges().length() > 0:
		TranslationServer.set_locale(original)

func _translate_field(event_type: String, section: String, field_key: String, fallback: String) -> String:
	var event_key = "ui.hud.event.%s.%s.%s" % [event_type, section, field_key]
	var text = _try_translate(event_key)
	if text.length() > 0:
		return text
	var shared_key = "ui.hud.event.shared.%s.%s" % [section, field_key]
	text = _try_translate(shared_key)
	if text.length() > 0:
		return text
	return fallback

func _publish_loot_granted(data_json: String) -> void:
	_bus.PublishSimple(EVENT_TYPE_LOOT_GRANTED, "ut", data_json)

func _publish_relic_applied(data_json: String) -> void:
	_bus.PublishSimple(EVENT_TYPE_RELIC_APPLIED, "ut", data_json)


# ACC:T62.3
# Loot granted events must surface source and effect fields in the HUD event log.
func test_task62_event_log_includes_loot_granted_details() -> void:
	var original_locale := _set_locale(LOCALE_ZH)
	var hud = await _hud()

	_publish_loot_granted("{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"LootKind\":\"relic\",\"MoneyDelta\":5,\"RelicId\":\"relic_gold_pouch\",\"SourceKind\":\"event_tile\",\"SourceId\":\"event_money_small\"}")
	for frame_index in range(60):
		if _event_log_messages(hud).size() > 0:
			break
		await get_tree().process_frame

	var details = _event_log_details(hud)
	var player_label = _translate_field(EVENT_TYPE_LOOT_GRANTED, "detail", "player_id", "player_id")
	var loot_label = _translate_field(EVENT_TYPE_LOOT_GRANTED, "detail", "loot_kind", "loot_kind")
	var relic_label = _translate_field(EVENT_TYPE_LOOT_GRANTED, "detail", "relic_id", "relic_id")
	var source_kind_label = _translate_field(EVENT_TYPE_LOOT_GRANTED, "detail", "source_kind", "source_kind")
	var source_id_label = _translate_field(EVENT_TYPE_LOOT_GRANTED, "detail", "source_id", "source_id")
	var money_label = _translate_field(EVENT_TYPE_LOOT_GRANTED, "delta", "money_delta", "money_delta")
	var loot_kind_value = _translate_token("loot_kind", "relic")
	var source_kind_value = _translate_token("source_kind", "event_tile")
	var relic_name = _require_translation("relic.relic_gold_pouch.name")
	var source_name = _require_translation("event.event_money_small.name")

	assert_str(details).contains(player_label + ": p1")
	assert_str(details).contains(loot_label + ": " + loot_kind_value)
	assert_str(details).contains(relic_label + ": " + relic_name)
	assert_str(details).contains(source_kind_label + ": " + source_kind_value)
	assert_str(details).contains(source_id_label + ": " + source_name)
	assert_str(details).contains(money_label + ": +5")

	_restore_locale(original_locale)


# ACC:T62.3
# Relic applied events must surface effect and delta fields in the HUD event log.
func test_task62_event_log_includes_relic_applied_details() -> void:
	var original_locale := _set_locale(LOCALE_ZH)
	var hud = await _hud()

	_publish_relic_applied("{\"GameId\":\"g1\",\"PlayerId\":\"p2\",\"RelicId\":\"relic_tax_ledger\",\"EffectKind\":\"economyStepDelta\",\"MoneyDelta\":0,\"StepDelta\":2}")
	for frame_index in range(60):
		if _event_log_messages(hud).size() > 0:
			break
		await get_tree().process_frame

	var details = _event_log_details(hud)
	var player_label = _translate_field(EVENT_TYPE_RELIC_APPLIED, "detail", "player_id", "player_id")
	var relic_label = _translate_field(EVENT_TYPE_RELIC_APPLIED, "detail", "relic_id", "relic_id")
	var effect_label = _translate_field(EVENT_TYPE_RELIC_APPLIED, "detail", "effect_kind", "effect_kind")
	var step_label = _translate_field(EVENT_TYPE_RELIC_APPLIED, "delta", "step_delta", "step_delta")
	var relic_name = _require_translation("relic.relic_tax_ledger.name")
	var effect_value = _translate_token("effect_kind", "economyStepDelta")

	assert_str(details).contains(player_label + ": p2")
	assert_str(details).contains(relic_label + ": " + relic_name)
	assert_str(details).contains(effect_label + ": " + effect_value)
	assert_str(details).contains(step_label + ": +2")

	_restore_locale(original_locale)
