namespace Game.Core.Ports;

public interface IResourceLoader
{
    string? LoadText(string path);
    byte[]? LoadBytes(string path);
}

