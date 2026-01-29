extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const _EVENT_KEYS: PackedStringArray = [
	"ui.hud.event.core.sanguo.economy.season.event.applied.title",
	"ui.hud.event.core.sanguo.economy.season.event.applied.summary",
	"ui.hud.event.core.sanguo.economy.season.event.applied.detail.game_id",
	"ui.hud.event.core.sanguo.economy.season.event.applied.detail.turn",
	"ui.hud.event.core.sanguo.economy.season.event.applied.detail.year",
	"ui.hud.event.core.sanguo.economy.season.event.applied.detail.season",
	"ui.hud.event.core.sanguo.economy.season.event.applied.detail.yield_multiplier",
	"ui.hud.event.core.sanguo.economy.season.event.applied.detail.affected_regions_count",
	"ui.hud.event.core.sanguo.economy.year.price.adjusted.title",
	"ui.hud.event.core.sanguo.economy.year.price.adjusted.summary",
	"ui.hud.event.core.sanguo.economy.year.price.adjusted.detail.game_id",
	"ui.hud.event.core.sanguo.economy.year.price.adjusted.detail.turn",
	"ui.hud.event.core.sanguo.economy.year.price.adjusted.detail.year",
	"ui.hud.event.core.sanguo.economy.year.price.adjusted.detail.city_id",
	"ui.hud.event.core.sanguo.economy.year.price.adjusted.detail.old_price",
	"ui.hud.event.core.sanguo.economy.year.price.adjusted.detail.new_price",
	"ui.hud.event.core.sanguo.city.toll.synergy.paid.title",
	"ui.hud.event.core.sanguo.city.toll.synergy.paid.summary",
	"ui.hud.event.core.sanguo.city.toll.synergy.paid.detail.game_id",
	"ui.hud.event.core.sanguo.city.toll.synergy.paid.detail.turn",
	"ui.hud.event.core.sanguo.city.toll.synergy.paid.detail.payer_id",
	"ui.hud.event.core.sanguo.city.toll.synergy.paid.detail.owner_id",
	"ui.hud.event.core.sanguo.city.toll.synergy.paid.detail.landing_city_id",
	"ui.hud.event.core.sanguo.city.toll.synergy.paid.detail.region_id",
	"ui.hud.event.core.sanguo.city.toll.synergy.paid.detail.expected_total_amount",
	"ui.hud.event.core.sanguo.city.toll.synergy.paid.detail.paid_total_amount",
	"ui.hud.event.core.sanguo.city.toll.synergy.paid.detail.expected_cities_count",
	"ui.hud.event.core.sanguo.city.toll.synergy.paid.detail.paid_cities_count",
]

const _LOCALES: PackedStringArray = ["en", "zh"]

func test_event_log_i18n_keys_present_for_season_year_synergy() -> void:
	assert_bool(FileAccess.file_exists("res://Game.Godot/Translations/ui_event_log.en.csv")).is_true()
	assert_bool(FileAccess.file_exists("res://Game.Godot/Translations/ui_event_log.zh.csv")).is_true()

	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())

	for locale in _LOCALES:
		if TranslationServer.has_method("set_locale"):
			TranslationServer.set_locale(String(locale))
		for key in _EVENT_KEYS:
			_translate_non_empty_or_fail(String(key))

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func _translate_non_empty_or_fail(key: String) -> String:
	assert_bool(key.strip_edges().length() > 0).is_true()
	var text := ""
	if TranslationServer.has_method("translate"):
		text = String(TranslationServer.translate(key))
	assert_bool(text.strip_edges().length() > 0).is_true()
	assert_bool(text != key).is_true()
	return text
