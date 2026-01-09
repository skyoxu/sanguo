using Godot;
using System;

namespace Game.Godot.Autoloads;

public partial class LocalizationBootstrap : Node
{
    private const string LocaleZh = "zh";
    private const string LocaleEn = "en";

    private static bool _initialized;

    public override void _EnterTree()
    {
        if (_initialized)
        {
            return;
        }

        _initialized = true;
        EnsureTutorialTranslations();
    }

    private static void EnsureTutorialTranslations()
    {
        EnsureLocale(LocaleEn, new (string Key, string Text)[]
        {
            ("help.tutorial.section.learning_route", "Learning route suggestions"),
            ("help.tutorial.section.team_knowledge_base", "Team knowledge base"),
            ("help.tutorial.step_01", "Step 01/06 - Roll dice\\nTrigger: Your turn starts.\\nAction: Click 'Roll Dice'.\\nResult: You get a dice value used for movement."),
            ("help.tutorial.step_02", "Step 02/06 - Move\\nTrigger: After rolling dice.\\nAction: The token moves by the dice value along the board path.\\nResult: You land on a tile and may trigger tile logic."),
            ("help.tutorial.step_03", "Step 03/06 - Buy/Pay\\nTrigger: You land on a city tile.\\nAction: Buy if unowned; otherwise pay toll to the owner.\\nResult: Ownership or money changes."),
            ("help.tutorial.step_04", "Step 04/06 - Month settlement\\nTrigger: Month boundary.\\nAction: Settlement runs for all players.\\nResult: Money updates based on owned cities and rules."),
            ("help.tutorial.step_05", "Step 05/06 - Season event\\nTrigger: After settlement (when applicable).\\nAction: A season event applies to the economy.\\nResult: Yields or modifiers change."),
            ("help.tutorial.step_06", "Step 06/06 - Yearly price adjustment\\nTrigger: Year boundary.\\nAction: City prices are adjusted.\\nResult: Future buy prices and yields may change."),
            ("help.tutorial.step_07", "Knowledge base 1/2 - Terms\\nDice: random value used for movement.\\nToll: money paid when landing on an owned city."),
            ("help.tutorial.step_08", "Knowledge base 2/2 - Consistency\\nKeep rules aligned with contracts and events.\\nPrefer deterministic tests for acceptance evidence."),
        });

        EnsureLocale(LocaleZh, new (string Key, string Text)[]
        {
            ("help.tutorial.section.learning_route", "\u5b66\u4e60\u8def\u7ebf\u5efa\u8bae"),
            ("help.tutorial.section.team_knowledge_base", "\u56e2\u961f\u77e5\u8bc6\u5e93"),
            ("help.tutorial.step_01", "\u6b65\u9aa4 01/06 - \u63b7\u9ab0\u5b50\\n\u89e6\u53d1\uff1a\u5f53\u524d\u56de\u5408\u5f00\u59cb\u3002\\n\u64cd\u4f5c\uff1a\u70b9\u51fb Roll Dice\u3002\\n\u7ed3\u679c\uff1a\u83b7\u5f97\u70b9\u6570\uff0c\u7528\u4e8e\u79fb\u52a8\u3002"),
            ("help.tutorial.step_02", "\u6b65\u9aa4 02/06 - \u79fb\u52a8\\n\u89e6\u53d1\uff1a\u63b7\u9ab0\u5b50\u540e\u3002\\n\u64cd\u4f5c\uff1a\u68cb\u5b50\u6309\u70b9\u6570\u6cbf\u68cb\u76d8\u8def\u5f84\u524d\u8fdb\u3002\\n\u7ed3\u679c\uff1a\u505c\u5728\u67d0\u4e2a\u683c\u5b50\uff0c\u53ef\u80fd\u89e6\u53d1\u683c\u5b50\u903b\u8f91\u3002"),
            ("help.tutorial.step_03", "\u6b65\u9aa4 03/06 - \u4e70\u5730/\u4ed8\u8d39\\n\u89e6\u53d1\uff1a\u505c\u5728\u57ce\u6c60\u683c\u5b50\u3002\\n\u64cd\u4f5c\uff1a\u65e0\u4e3b\u57ce\u6c60\u53ef\u9009\u62e9\u8d2d\u4e70\uff1b\u4ed6\u4eba\u57ce\u6c60\u9700\u652f\u4ed8\u8fc7\u8def\u8d39\u3002\\n\u7ed3\u679c\uff1a\u6240\u6709\u6743\u6216\u8d44\u91d1\u53d1\u751f\u53d8\u5316\u3002"),
            ("help.tutorial.step_04", "\u6b65\u9aa4 04/06 - \u6708\u672b\u7ed3\u7b97\\n\u89e6\u53d1\uff1a\u8de8\u6708\u8282\u70b9\u3002\\n\u64cd\u4f5c\uff1a\u7cfb\u7edf\u4e3a\u6240\u6709\u73a9\u5bb6\u6267\u884c\u7ed3\u7b97\u3002\\n\u7ed3\u679c\uff1a\u8d44\u91d1\u6309\u5df2\u6709\u8d44\u4ea7\u4e0e\u89c4\u5219\u66f4\u65b0\u3002"),
            ("help.tutorial.step_05", "\u6b65\u9aa4 05/06 - \u5b63\u8282\u4e8b\u4ef6\\n\u89e6\u53d1\uff1a\u7ed3\u7b97\u540e(\u7b26\u5408\u6761\u4ef6\u65f6)\u3002\\n\u64cd\u4f5c\uff1a\u5b63\u8282\u4e8b\u4ef6\u5bf9\u7ecf\u6d4e\u4ea7\u751f\u5f71\u54cd\u3002\\n\u7ed3\u679c\uff1a\u6536\u76ca\u6216\u4fee\u6b63\u7cfb\u6570\u6539\u53d8\u3002"),
            ("help.tutorial.step_06", "\u6b65\u9aa4 06/06 - \u5e74\u5ea6\u5730\u4ef7\u8c03\u6574\\n\u89e6\u53d1\uff1a\u8de8\u5e74\u8282\u70b9\u3002\\n\u64cd\u4f5c\uff1a\u57ce\u6c60\u4ef7\u683c\u8fdb\u884c\u8c03\u6574\u3002\\n\u7ed3\u679c\uff1a\u540e\u7eed\u8d2d\u4e70\u6210\u672c\u4e0e\u6536\u76ca\u4f1a\u53d7\u5f71\u54cd\u3002"),
            ("help.tutorial.step_07", "\u77e5\u8bc6\u5e93 1/2 - \u672f\u8bed\\n\u9ab0\u5b50\uff1a\u7528\u4e8e\u51b3\u5b9a\u79fb\u52a8\u6b65\u6570\u7684\u968f\u673a\u503c\u3002\\n\u8fc7\u8def\u8d39\uff1a\u505c\u5728\u4ed6\u4eba\u57ce\u6c60\u65f6\u652f\u4ed8\u7684\u91d1\u989d\u3002"),
            ("help.tutorial.step_08", "\u77e5\u8bc6\u5e93 2/2 - \u53e3\u5f84\\n\u89c4\u5219\u4ee5 Contracts/\u4e8b\u4ef6\u4e3a\u51c6\uff0c\u907f\u514d UI \u5f15\u5165\u591a\u4e2a\u5199\u5165\u53e3\u5f84\u3002\\n\u5c3d\u91cf\u7528\u786e\u5b9a\u6027\u6d4b\u8bd5\u4f5c\u4e3a\u9a8c\u6536\u8bc1\u636e\u3002"),
        });
    }

    private static void EnsureLocale(string locale, (string Key, string Text)[] entries)
    {
        if (string.IsNullOrWhiteSpace(locale))
        {
            return;
        }

        var translation = new Translation();
        translation.Locale = locale;

        foreach (var (key, text) in entries)
        {
            if (string.IsNullOrWhiteSpace(key) || string.IsNullOrWhiteSpace(text))
            {
                continue;
            }

            translation.Call("add_message", key, text);
        }

        TranslationServer.AddTranslation(translation);

        try
        {
            // Ensure at least one non-empty locale is set for tests that read TranslationServer.get_locale().
            if (TranslationServer.GetLocale().Length == 0)
            {
                TranslationServer.SetLocale(locale);
            }
        }
        catch
        {
        }
    }
}
