# Arcade High Score Board - Design

## Where It Lives

**After game over / you win, before returning to intro.** The flow becomes:

```
Game Over / You Win screen
    -> F+J press
    -> High Score Board (always shown)
        -> If score qualifies: Name entry -> Animated insertion
        -> If not: Board displayed with current score shown dimmed at bottom
    -> F+J to exit to Intro screen
```

The high score board always appears after game over / you win. This gives every player context for how they performed relative to past games. If the score qualifies for the top 10, the name entry and insertion animation play. If not, the board is shown as-is with the player's current score displayed below the board in a dimmed style so they can see how close they were.

## Name Entry

Use the existing 6-button input system (S, D, F, J, K, L) mapped to letter cycling:

- **Any left-hand button (S, D, F):** Cycle letter backward (Z -> Y -> X...)
- **Any right-hand button (J, K, L):** Cycle letter forward (A -> B -> C...)
- **F + J simultaneous:** Confirm current letter and advance to next position

3-character name (classic arcade style). Each position shows the current letter in a large hexagon with the button-colored cycling arrows on either side. Unconfirmed letters pulse. Confirmed letters lock in with a small explosion + sound.

After all 3 letters confirmed, brief pause, then the insertion animation plays.

## High Score Entry Data

Each entry stores:

```python
{
    "name": "AAA",           # 3 characters
    "score": 4250,           # Final score
    "wave": 12,              # Waves completed (wave - 1)
    "bosses": 2,             # Bosses defeated (wave // 4)
    "difficulty": "HARD",    # Difficulty setting
    "perfect_waves": 3,      # Perfect wave count
    "timestamp": "..."       # ISO timestamp
}
```

## Board Display

10 entries displayed in a vertical list, each row showing:

```
 1. ACE   4250  W12  [diamond][diamond]  ***   HARD
 2. BOB   3100  W08  [diamond]           **    NORMAL
 3. ---   ----  ---  ---                 ---   ---
```

- **Rank:** 1-10, left-aligned
- **Name:** 3 chars, button-colored per character
- **Score:** Right-aligned, comma-formatted
- **Waves:** "W" + wave count
- **Bosses:** Red diamond pips (reusing the boss pip visual from wave transition)
- **Perfect waves:** Yellow star/pip per perfect wave (max 5, then "+N")
- **Difficulty:** Color-coded text (green/yellow/red)

Rows use the waveform aesthetic - thin cyan horizontal lines connecting the data fields, dimmer for lower ranks.

## Insertion Animation Sequence

When a new high score qualifies:

1. **Board appears** with existing entries in final positions
2. **New entry slides in from the right** at the qualifying rank position, glowing bright
3. **Screen flash** (starfield.start_flash) + explosion sound (thunder_1 for dramatic impact)
4. **Entries below get "knocked down"** - they animate downward one position with a bounce/settle easing, each staggered by ~100ms
5. **Each displaced entry triggers a small explosion ring** at its original position as it moves (reuse ExplosionRing, cyan colored, small radius)
6. **Entry #10 falls off the bottom** if the board was full - slides down and fades out
7. **The new entry pulses/glows** for 1-2 seconds after settling
8. **Sound cascade:** explosion on impact, then quieter pops for each displaced entry rippling downward

## Persistence

Store in `config/high_scores.json`:

```json
{
    "scores": [
        {"name": "ACE", "score": 4250, "wave": 12, ...},
        ...
    ]
}
```

Load on game start, save after each new entry. Max 10 entries. The file lives alongside the existing config JSON files.

## Visual Style

- Background: dim starfield (same as intro/game over)
- Title: "HIGH SCORES" in the title font, cyan, centered top
- Entry text: Orbitron font (same as HUD), smaller size
- New entry: magenta glow (matching the orb color from wave transition)
- Existing entries: cyan with decreasing brightness by rank
- Connecting lines: thin horizontal waveform segments between fields
- The whole board has a slight CRT scan-line effect (alternating row opacity)

## Exit

After the insertion animation completes (~2 seconds), F+J exits to intro. The board stays visible until dismissed, no auto-timeout.

## Edge Cases

- First game ever: board is empty, first score always qualifies
- Score of 0: does not qualify for entry, board still shown (empty or with prior scores)
- Tied scores: new entry goes above existing entries with the same score
- Board not full (<10 entries): always qualifies if score > 0
- Non-qualifying score: board shown read-only, player's score displayed dimmed below the list with "YOUR SCORE: 150" so they see the gap to beat
