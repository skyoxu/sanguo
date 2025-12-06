using Godot;
using Game.Core.Ports;

namespace Game.Godot.Adapters;

public partial class AudioPlayerAdapter : Node, IAudioPlayer
{
    private AudioStreamPlayer _sfx = default!;
    private AudioStreamPlayer _music = default!;

    public override void _Ready()
    {
        _sfx = new AudioStreamPlayer { Name = "SfxPlayer" };
        _music = new AudioStreamPlayer { Name = "MusicPlayer" };
        AddChild(_sfx);
        AddChild(_music);
    }

    public void PlaySfx(string id, float volume = 1f)
    {
        var stream = ResourceLoader.Load<AudioStream>(id);
        if (stream == null) return;
        _sfx.Stream = stream;
        _sfx.VolumeDb = Mathf.LinearToDb(Mathf.Clamp(volume, 0, 1));
        _sfx.Play();
    }

    public void PlayMusic(string id, float volume = 1f, bool loop = true)
    {
        var stream = ResourceLoader.Load<AudioStream>(id);
        if (stream == null) return;
        if (stream is AudioStreamOggVorbis ogg)
        {
            ogg.Loop = loop;
        }
        _music.Stop();
        _music.Stream = stream;
        _music.VolumeDb = Mathf.LinearToDb(Mathf.Clamp(volume, 0, 1));
        _music.Play();
    }

    public void StopMusic() => _music.Stop();
}
