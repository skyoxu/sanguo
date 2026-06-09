extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const SFX_ID := "res://Game.Godot/Assets/Audio/ui_click.wav"
const MUSIC_ID := "res://Game.Godot/Assets/Audio/music_loop.wav"

# ACC:T189.1
# ACC:T189.5
# ACC:T189.8
# ACC:T27.1
# ACC:T188.12
# ACC:T190.1
# ACC:T193.1
# ACC:T193.2
# ACC:T193.3
# ACC:T193.4
# ACC:T220.1
# ACC:T220.4
# ACC:T220.6
# ACC:T205.1
# ACC:T205.5
# ACC:T205.10
# ACC:T205.12
func test_audio_player_adapter_creates_sfx_and_music_players_on_ready() -> void:
	var adapter := preload("res://Game.Godot/Adapters/AudioPlayerAdapter.cs").new()
	add_child(auto_free(adapter))
	await get_tree().process_frame

	var sfx: AudioStreamPlayer = adapter.get_node_or_null("SfxPlayer")
	var music: AudioStreamPlayer = adapter.get_node_or_null("MusicPlayer")
	assert_object(sfx).is_not_null()
	assert_object(music).is_not_null()

	adapter.call("PlayMusic", MUSIC_ID, 0.8, true)
	await get_tree().process_frame
	assert_object(music.stream).is_not_null()
	assert_object(music.get_stream_playback()).is_not_null()
	assert_bool(music.playing).is_true()

	adapter.call("PlaySfx", SFX_ID, 1.0)
	await get_tree().process_frame
	assert_object(sfx.stream).is_not_null()
	assert_object(sfx.get_stream_playback()).is_not_null()
	assert_bool(music.playing).is_true()

	adapter.call("StopMusic")
	await get_tree().process_frame
	assert_bool(music.playing).is_false()
	assert_object(sfx.stream).is_not_null()

# ACC:T220.1
# ACC:T220.4
# ACC:T220.6
func test_task220_audio_adapter_preserves_existing_playback_contract_when_optional_state_is_added() -> void:
	var adapter := preload("res://Game.Godot/Adapters/AudioPlayerAdapter.cs").new()
	add_child(auto_free(adapter))
	await get_tree().process_frame

	var music: AudioStreamPlayer = adapter.get_node_or_null("MusicPlayer")
	assert_object(music).is_not_null()

	adapter.call("PlayMusic", MUSIC_ID, 0.8, true)
	await get_tree().process_frame
	assert_bool(music.playing).is_true()
	assert_object(music.stream).is_not_null()

	adapter.call("PlayMusic", MUSIC_ID, 0.5, true)
	await get_tree().process_frame
	assert_bool(music.playing).is_true()
	assert_object(music.stream).is_not_null()

# ACC:T27.5
# ACC:T188.17
func test_audio_player_adapter_handles_missing_audio_resources_without_throwing() -> void:
	var adapter := preload("res://Game.Godot/Adapters/AudioPlayerAdapter.cs").new()
	add_child(auto_free(adapter))
	await get_tree().process_frame

	var sfx: AudioStreamPlayer = adapter.get_node_or_null("SfxPlayer")
	var music: AudioStreamPlayer = adapter.get_node_or_null("MusicPlayer")
	assert_object(sfx).is_not_null()
	assert_object(music).is_not_null()

	adapter.call("PlaySfx", SFX_ID, 1.0)
	adapter.call("PlayMusic", MUSIC_ID, 0.8, true)
	await get_tree().process_frame

	assert_object(sfx.stream).is_not_null()
	assert_object(music.stream).is_not_null()
	assert_object(sfx.get_stream_playback()).is_not_null()
	assert_bool(music.playing).is_true()

	var sfx_stream_before := sfx.stream
	var music_stream_before := music.stream

	# These resource ids are intentionally missing; adapter should fail-safe (no throw).
	adapter.call("PlaySfx", "res://__missing__/sfx.wav", 1.0)
	adapter.call("PlayMusic", "res://__missing__/music.ogg", 1.0, true)
	await get_tree().process_frame

	# ACC:T27.5
	assert_bool(music.playing).is_true()
	assert_bool(sfx.stream == sfx_stream_before).is_true()
	assert_bool(music.stream == music_stream_before).is_true()

	adapter.call("StopMusic")
	await get_tree().process_frame

	assert_bool(adapter.is_inside_tree()).is_true()
