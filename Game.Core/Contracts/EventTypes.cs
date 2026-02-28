namespace Game.Core.Contracts;

/// <summary>
/// Stable domain event type constants (CloudEvents-like type values).
/// </summary>
/// <remarks>
/// ADR refs: ADR-0004, ADR-0020.
/// Overlay ref: docs/architecture/overlays/PRD-NEWROUGE-GAME-0001/08/08-Contracts-M1.md
/// </remarks>
public static class EventTypes
{
    public const string ActConfigLoaded = "core.act.config.loaded";
    public const string AuditLogged = "core.audit.logged";
    public const string AutosaveWritten = "core.autosave.written";
    public const string CardUltimatePromoted = "core.card.ultimate.promoted";
    public const string CardUpgraded = "core.card.upgraded";
    public const string CombatCardInvalidPlayBlocked = "core.combat.card.invalid_play_blocked";
    public const string CombatCardPlayed = "core.combat.card.played";
    public const string CombatDamageResolved = "core.combat.damage.resolved";
    public const string CombatEnded = "core.combat.ended";
    public const string CombatFixedDamageResolved = "core.combat.fixed_damage.resolved";
    public const string CombatLoopHardStopped = "core.combat.loop.hard_stopped";
    public const string CombatStarted = "core.combat.started";
    public const string CombatTurnStarted = "core.combat.turn.started";
    public const string CurseAdded = "core.curse.added";
    public const string CurseRemoved = "core.curse.removed";
    public const string DarkCostApplied = "core.darkcost.applied";
    public const string DeckDiscarded = "core.deck.discarded";
    public const string DeckDrawn = "core.deck.drawn";
    public const string DeckExhausted = "core.deck.exhausted";
    public const string DeckInitialized = "core.deck.initialized";
    public const string DeckRetained = "core.deck.retained";
    public const string DeckShuffled = "core.deck.shuffled";
    public const string DifficultyModifierApplied = "core.difficulty.modifier.applied";
    public const string EventChoiceCommitted = "core.event.choice.committed";
    public const string EventEntered = "core.event.entered";
    public const string IntentSelected = "core.intent.selected";
    public const string MapNodeEntered = "core.map.node.entered";
    public const string MapNodeLocked = "core.map.node.locked";
    public const string MapNodeSelected = "core.map.node.selected";
    public const string MapPathBacktrackBlocked = "core.map.path.backtrack.blocked";
    public const string RelicGranted = "core.relic.granted";
    public const string RestOptionSelected = "core.rest.option.selected";
    public const string RewardOfferLocked = "core.reward.offer.locked";
    public const string RewardOfferPresented = "core.reward.offer.presented";
    public const string RewardOfferSelected = "core.reward.offer.selected";
    public const string RewardOfferSkipped = "core.reward.offer.skipped";
    public const string RngStreamAdvanced = "core.rng.stream.advanced";
    public const string RngStreamRestored = "core.rng.stream.restored";
    public const string RunCharacterSelected = "core.run.character.selected";
    public const string RunContinueBlocked = "core.run.continue.blocked";
    public const string RunDifficultySelected = "core.run.difficulty.selected";
    public const string RunResumed = "core.run.resumed";
    public const string RunStarted = "core.run.started";
    public const string RunStateTransitioned = "core.run.state.transitioned";
    public const string SaveLoaded = "core.save.loaded";
    public const string SaveMigrationFailed = "core.save.migration.failed";
    public const string SaveWriteFailed = "core.save.write.failed";
    public const string SaveWriteSucceeded = "core.save.write.succeeded";
    public const string ShopCurseRemoved = "core.shop.curse.removed";
    public const string ShopInventoryLocked = "core.shop.inventory.locked";
    public const string ShopItemPurchased = "core.shop.item.purchased";
    public const string StatusApplied = "core.status.applied";
    public const string StatusDispelled = "core.status.dispelled";
    public const string StatusExpired = "core.status.expired";
    public const string StatusStacked = "core.status.stacked";
    public const string TraceabilityChecked = "core.traceability.checked";
    public const string GuildMemberJoined = "core.guild.member.joined";
    public const string ScoreUpdated = "core.score.updated";
    public const string HealthUpdated = "core.health.updated";
}
