extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# ACC:T27.1
func test_audio_player_adapter_creates_sfx_and_music_players_on_ready() -> void:
	var adapter := preload("res://Game.Godot/Adapters/AudioPlayerAdapter.cs").new()
	add_child(auto_free(adapter))
	await get_tree().process_frame

	assert_object(adapter.get_node_or_null("SfxPlayer")).is_not_null()
	assert_object(adapter.get_node_or_null("MusicPlayer")).is_not_null()
