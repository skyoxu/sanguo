extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const UI_MENU_START := "ui.menu.start"

func _ensure_event_bus() -> Node:
    var existing := get_node_or_null("/root/EventBus")
    if existing != null:
        existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
        existing.queue_free()

    var bus := preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(bus))
    return bus

func test_audio_server_has_master_bus() -> void:
    var master := AudioServer.get_bus_index("Master")
    assert_int(master).is_greater_equal(0)

# ACC:T27.2
func test_sanguo_main_music_autoplays_when_music_player_present() -> void:
    var bus := _ensure_event_bus()
    assert_bool(bus.is_inside_tree()).is_true()
    assert_bool(bus.has_method("PublishSimple")).is_true()

    var main := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(auto_free(main))
    await get_tree().process_frame
    assert_bool(main.is_inside_tree()).is_true()
    assert_bool(main.visible).is_true()

    bus.call("PublishSimple", UI_MENU_START, "gdunit", "{}")
    for _i in range(0, 10):
        await get_tree().process_frame

    var music: AudioStreamPlayer = main.get_node_or_null("Audio/MusicPlayer")
    assert_object(music).is_not_null()
    assert_object(music.stream).is_not_null()
    assert_bool(music.playing).is_true()

    # ACC:T27.2
    var stream := music.stream
    if stream is AudioStreamWav:
        var wav: AudioStreamWav = stream
        assert_int(wav.loop_mode).is_not_equal(AudioStreamWav.LOOP_DISABLED)
    elif stream is AudioStreamOggVorbis:
        var ogg: AudioStreamOggVorbis = stream
        assert_bool(ogg.loop).is_true()
