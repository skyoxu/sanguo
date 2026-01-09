extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const _TUTORIAL_KEY_HINTS: PackedStringArray = [
	"help",
	"tutorial",
	"onboarding",
	"howto",
	"guide",
	"knowledge"
]

const _REQUIRED_STEP_KEYS: PackedStringArray = [
	"help.tutorial.step_01",
	"help.tutorial.step_02",
	"help.tutorial.step_03",
	"help.tutorial.step_04",
	"help.tutorial.step_05",
	"help.tutorial.step_06",
]

const _LOCALE_ZH := "zh"
const _KW_ROLL_DICE := "\u63b7\u9ab0\u5b50"
const _KW_MOVE := "\u79fb\u52a8"
const _KW_BUY := "\u4e70\u5730"
const _KW_PAY := "\u4ed8\u8d39"
const _KW_MONTH_SETTLEMENT := "\u6708\u672b\u7ed3\u7b97"
const _KW_SEASON_EVENT := "\u5b63\u8282\u4e8b\u4ef6"
const _KW_YEAR_PRICE_ADJUST := "\u5e74\u5ea6\u5730\u4ef7\u8c03\u6574"
const _KW_TRIGGER := "\u89e6\u53d1"
const _KW_ACTION := "\u64cd\u4f5c"
const _KW_RESULT := "\u7ed3\u679c"

func test_translation_server_locale_is_non_empty() -> void:
	var locale := ""
	if TranslationServer.has_method("get_locale"):
		locale = String(TranslationServer.get_locale())
	assert_bool(locale.strip_edges().length() > 0).is_true()

func test_tutorial_key_heuristic_is_deterministic() -> void:
	assert_bool(_looks_like_tutorial_key("help.tutorial.step_01")).is_true()
	assert_bool(_looks_like_tutorial_key("ui.menu.start")).is_false()

# acceptance: ACC:T30.4
func test_help_tutorial_localized_content_entries_are_present_and_non_empty() -> void:
	assert_bool(FileAccess.file_exists("res://Game.Godot/Translations/help_tutorial.en.csv")).is_true()
	assert_bool(FileAccess.file_exists("res://Game.Godot/Translations/help_tutorial.zh.csv")).is_true()

	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())

	var locales := _get_loaded_locales_safe(original_locale)
	assert_bool(locales.is_empty()).is_false()

	var target_locale := ""
	for l in locales:
		if String(l) == _LOCALE_ZH:
			target_locale = _LOCALE_ZH
			break
	if target_locale.is_empty():
		target_locale = String(locales[0])

	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(target_locale)

	var step_texts := {}
	for key in _REQUIRED_STEP_KEYS:
		step_texts[String(key)] = _translate_non_empty_or_fail(String(key))

	# Must cover the T2 loop topics in a step-by-step progression (each step has trigger/action/result).
	_assert_step_has_structure_and_keyword(step_texts["help.tutorial.step_01"], _KW_ROLL_DICE)
	_assert_step_has_structure_and_keyword(step_texts["help.tutorial.step_02"], _KW_MOVE)
	_assert_step_has_structure_and_keyword(step_texts["help.tutorial.step_03"], _KW_BUY)
	# Allow either keyword for the buy/pay step.
	assert_bool(String(step_texts["help.tutorial.step_03"]).find(_KW_PAY) != -1).is_true()
	_assert_step_has_structure_and_keyword(step_texts["help.tutorial.step_04"], _KW_MONTH_SETTLEMENT)
	_assert_step_has_structure_and_keyword(step_texts["help.tutorial.step_05"], _KW_SEASON_EVENT)
	_assert_step_has_structure_and_keyword(step_texts["help.tutorial.step_06"], _KW_YEAR_PRICE_ADJUST)

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func _assert_step_has_structure_and_keyword(text: String, keyword: String) -> void:
	assert_bool(text.strip_edges().length() > 0).is_true()
	assert_bool(text.find(keyword) != -1).is_true()
	assert_bool(text.find(_KW_TRIGGER) != -1).is_true()
	assert_bool(text.find(_KW_ACTION) != -1).is_true()
	assert_bool(text.find(_KW_RESULT) != -1).is_true()

func _translate_non_empty_or_fail(key: String) -> String:
	assert_bool(key.strip_edges().length() > 0).is_true()

	var text := ""
	if TranslationServer.has_method("translate"):
		text = String(TranslationServer.translate(key))
	assert_bool(text.strip_edges().length() > 0).is_true()
	assert_bool(text != key).is_true()
	return text

func _get_loaded_locales_safe(fallback_locale: String) -> PackedStringArray:
	if TranslationServer.has_method("get_loaded_locales"):
		var loaded: PackedStringArray = TranslationServer.get_loaded_locales()
		if not loaded.is_empty():
			return loaded
	var single: PackedStringArray = []
	if fallback_locale.strip_edges().length() > 0:
		single.append(fallback_locale)
	return single

func _looks_like_tutorial_key(key: String) -> bool:
	var lower := key.to_lower()
	for hint in _TUTORIAL_KEY_HINTS:
		if lower.find(String(hint)) != -1:
			return true
	return false
