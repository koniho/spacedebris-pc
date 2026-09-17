"""Enemy classes and animations."""

from enemies.base_enemy import BaseEnemy
from enemies.enemy import Enemy
from enemies.rapid_hit_enemy import RapidHitEnemy
from enemies.linked_enemy_pair import LinkedEnemyPair
from enemies.reverse_enemy import ReverseEnemy
from enemies.shielded_enemy import ShieldedEnemy
from enemies.forcefield_boss import ForcefieldBoss
from enemies.face_boss import FaceBoss
from enemies.animations import EnemyVictoryDeathAnimation, EnemyFireDeathAnimation
from enemies.letter_effects import (
    LetterActivationAnim,
    EnemyLetterRingEffect,
    HexagonFlashAnim,
)

__all__ = [
    "BaseEnemy",
    "Enemy",
    "RapidHitEnemy",
    "LinkedEnemyPair",
    "ReverseEnemy",
    "ShieldedEnemy",
    "ForcefieldBoss",
    "FaceBoss",
    "EnemyVictoryDeathAnimation",
    "EnemyFireDeathAnimation",
    "LetterActivationAnim",
    "EnemyLetterRingEffect",
    "HexagonFlashAnim",
]
