namespace Game.Core.Ports;

public interface IAudioPlayer
{
    void PlaySfx(string id, float volume = 1f);
    void PlayMusic(string id, float volume = 1f, bool loop = true);
    void StopMusic();
}

