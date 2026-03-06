extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const UI_MENU_START := "ui.menu.start"
const CORE_TURN_STARTED := "core.sanguo.game.turn.started"

var _events: Array = []

func _ensure_event_bus() -> Node:
    var existing := get_node_or_null("/root/EventBus")
    if existing != null:
        existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
        existing.queue_free()

    var bus := preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(bus))
    return bus


func _on_domain_event_emitted(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
    _events.append({"type": str(type)})


func _has_event(type_name: String) -> bool:
    for e in _events:
        if str(e.get("type", "")) == type_name:
            return true
    return false

func test_audio_server_has_master_bus() -> void:
    var master := AudioServer.get_bus_index("Master")
    assert_int(master).is_greater_equal(0)

# ACC:T27.2
func test_sanguo_main_music_autoplays_when_music_player_present() -> void:
    var bus := _ensure_event_bus()
    assert_bool(bus.is_inside_tree()).is_true()
    assert_bool(bus.has_method("PublishSimple")).is_true()
    bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event_emitted"))
    _events = []

    var main := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(auto_free(main))
    await get_tree().process_frame
    assert_bool(main.is_inside_tree()).is_true()
    assert_bool(main.visible).is_true()

    bus.call("PublishSimple", UI_MENU_START, "gdunit", "{}")
    for _i in range(0, 180):
        await get_tree().process_frame
        if _has_event(CORE_TURN_STARTED):
            break
    assert_bool(_has_event(CORE_TURN_STARTED)).is_true()

    var music: AudioStreamPlayer = main.get_node_or_null("Audio/MusicPlayer")
    assert_object(music).is_not_null()
    for _i in range(0, 60):
        if music.playing and music.stream != null:
            break
        await get_tree().process_frame
    assert_object(music.stream).is_not_null()
    assert_bool(music.playing).is_true()

    # ACC:T27.2
    var stream := music.stream
    if stream is AudioStreamWAV:
        var wav: AudioStreamWAV = stream
        assert_int(wav.loop_mode).is_not_equal(AudioStreamWAV.LOOP_DISABLED)
    elif stream is AudioStreamOggVorbis:
        var ogg: AudioStreamOggVorbis = stream
        assert_bool(ogg.loop).is_true()
