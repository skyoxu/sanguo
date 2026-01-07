using Godot;
using Game.Core.Ports;
using System;

namespace Game.Godot.Adapters;

public partial class AudioPlayerAdapter : Node, IAudioPlayer
{
    private const string DefaultUiClickSfxId = "res://Game.Godot/Assets/Audio/ui_click.wav";
    private const string DefaultMusicLoopId = "res://Game.Godot/Assets/Audio/music_loop.wav";

    private AudioStreamPlayer _sfx = default!;
    private AudioStreamPlayer _music = default!;

    private static AudioStreamWav? _cachedUiClick;
    private static AudioStreamWav? _cachedMusicLoop;

    public override void _Ready()
    {
        _sfx = new AudioStreamPlayer { Name = "SfxPlayer" };
        _music = new AudioStreamPlayer { Name = "MusicPlayer" };
        AddChild(_sfx);
        AddChild(_music);
    }

    public void PlaySfx(string id, float volume = 1f)
    {
        var stream = ResolveAudioStream(id, isMusic: false, loop: false);
        if (stream == null)
        {
            return;
        }
        _sfx.Stream = stream;
        _sfx.VolumeDb = Mathf.LinearToDb(Mathf.Clamp(volume, 0, 1));
        _sfx.Play();
    }

    public void PlayMusic(string id, float volume = 1f, bool loop = true)
    {
        var stream = ResolveAudioStream(id, isMusic: true, loop: loop);
        if (stream == null)
        {
            return;
        }
        if (stream is AudioStreamOggVorbis ogg)
        {
            ogg.Loop = loop;
        }
        else if (stream is AudioStreamWav wav)
        {
            wav.LoopMode = loop ? AudioStreamWav.LoopModeEnum.Forward : AudioStreamWav.LoopModeEnum.Disabled;
            wav.LoopBegin = 0;
            int bytesPerFrame = wav.Stereo ? 4 : 2;
            wav.LoopEnd = bytesPerFrame <= 0 ? 0 : wav.Data.Length / bytesPerFrame;
        }
        _music.Stop();
        _music.Stream = stream;
        _music.VolumeDb = Mathf.LinearToDb(Mathf.Clamp(volume, 0, 1));
        _music.Play();
    }

    public void StopMusic() => _music.Stop();

    private static AudioStream? ResolveAudioStream(string id, bool isMusic, bool loop)
    {
        if (string.Equals(id, DefaultUiClickSfxId, StringComparison.Ordinal))
        {
            return _cachedUiClick ??= CreateToneWav(880f, 0.12f, 0.18f, loop: false);
        }

        if (string.Equals(id, DefaultMusicLoopId, StringComparison.Ordinal))
        {
            return _cachedMusicLoop ??= CreateToneWav(220f, 1.0f, 0.10f, loop: loop);
        }

        if (!ResourceLoader.Exists(id))
        {
            return null;
        }

        return ResourceLoader.Load<AudioStream>(id);
    }

    private static AudioStreamWav CreateToneWav(float frequencyHz, float seconds, float amplitude, bool loop)
    {
        const int sampleRate = 44100;
        int total = Math.Max(1, (int)(sampleRate * Math.Max(0.01f, seconds)));
        int fade = (int)(sampleRate * 0.015f);

        short[] pcm = new short[total];
        double omega = 2.0 * Math.PI * frequencyHz;
        for (int i = 0; i < total; i++)
        {
            double t = (double)i / sampleRate;
            double env = 1.0;
            if (fade > 0)
            {
                if (i < fade) env = (double)i / fade;
                else if (i > total - fade) env = Math.Max(0.0, (double)(total - i) / fade);
            }

            double v = amplitude * env * Math.Sin(omega * t);
            pcm[i] = (short)Math.Clamp((int)(v * short.MaxValue), short.MinValue, short.MaxValue);
        }

        byte[] bytes = new byte[pcm.Length * 2];
        Buffer.BlockCopy(pcm, 0, bytes, 0, bytes.Length);

        var wav = new AudioStreamWav
        {
            MixRate = sampleRate,
            Stereo = false,
            Format = AudioStreamWav.FormatEnum.Format16Bits,
            Data = bytes,
        };

        wav.LoopMode = loop ? AudioStreamWav.LoopModeEnum.Forward : AudioStreamWav.LoopModeEnum.Disabled;
        wav.LoopBegin = 0;
        wav.LoopEnd = pcm.Length;
        return wav;
    }
}
