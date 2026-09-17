"""Sound manager using PyQt5."""

import os
from debug_log import debug_print as print
import random
from typing import List
from PyQt5.QtCore import QUrl, QFile
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist, QSoundEffect
from PyQt5.QtCore import QTimer


class SoundManager:
    """Manages background music and sound effects using PyQt5."""

    def __init__(self, sounds_dir: str = None, enabled: bool = True, use_resources: bool = False):
        """Initialize sound manager.

        Args:
            sounds_dir: Filesystem path to sounds (for development)
            enabled: Whether sound is enabled
            use_resources: If True, load from Qt resources (:/sounds/)
        """
        self.sounds_dir = sounds_dir
        self.use_resources = use_resources
        self.enabled = enabled

        # Background music players (two for gapless looping)
        self.music_player_a = QMediaPlayer()
        self.music_player_b = QMediaPlayer()
        self.music_player = self.music_player_a  # Current active player
        self.music_file_url = None
        self.music_duration = 0
        self.music_loop_check_timer = None
        self.music_crossfade_ms = 100  # Crossfade duration in ms

        # Sound effects using QSoundEffect for low-latency playback
        self.laser_effects: List[QSoundEffect] = []
        self.explosion_effects: List[QSoundEffect] = []
        self.player_hit_effect = None
        self.player_hit_2_effect = None  # Final hit when player dies
        self.whoosh_1_effect = None  # Wave transition start
        self.whoosh_2_effect = None  # Wave transition end
        self.denied_1_effect = None  # Shield block denied
        self.denied_2_effect = None  # Wrong key denied
        self.twinkle_effect = None  # New effect for intro/game start
        self.thunder_effect = None  # Thunder for boss entry flashes
        self.disable_cone_effect = None
        self.fire_cone_effect = None

        # Minor scale sounds for intro screen
        self.minor_scale_effects: List[QSoundEffect] = []
        self.minor_scale_index = 0

        # Game over music player (separate from main background music)
        self.gameover_player = QMediaPlayer()
        self.gameover_music_loaded = False

        # You win music player (separate from main background music)
        self.youwin_player = QMediaPlayer()
        self.youwin_music_loaded = False
        self.youwin_fade_timer = None

        # Round-robin indices for each effect type
        self.laser_index = 0
        self.explosion_index = 0

        # Fade state
        self.fade_timer = None
        self.fade_duration = 0
        self.fade_start_volume = 0
        self.fade_target_volume = 0
        self.fade_elapsed = 0
        self._pause_premute_volume = None

        # Initialize
        self._load_sounds()

    def _get_sound_url(self, filename: str) -> QUrl:
        """Get QUrl for a sound file from resources or filesystem."""
        if self.use_resources:
            return QUrl(f"qrc:/sounds/{filename}")
        else:
            filepath = os.path.join(self.sounds_dir, filename)
            return QUrl.fromLocalFile(os.path.abspath(filepath))

    def _sound_exists(self, filename: str) -> bool:
        """Check if sound file exists in resources or filesystem."""
        if self.use_resources:
            return QFile.exists(f":/sounds/{filename}")
        else:
            return os.path.exists(os.path.join(self.sounds_dir, filename))

    def _load_sounds(self):
        """Load all sound files."""
        # Load laser sounds using QSoundEffect (WAV only - QSoundEffect doesn't support MP3 well)
        for i in range(1, 4):  # laser_1.wav through laser_3.wav
            filename = f"laser_{i}.wav"
            if self._sound_exists(filename):
                # Create multiple QSoundEffect instances for overlapping sounds
                for _ in range(2):  # 2 instances per sound for overlap
                    effect = QSoundEffect()
                    effect.setSource(self._get_sound_url(filename))
                    effect.setVolume(0.3)  # 30% volume
                    effect.setLoopCount(1)  # Play once
                    self.laser_effects.append(effect)
                print(f"Loaded laser sound effect: {filename}")

        # Load explosion sounds using QSoundEffect (WAV only)
        for i in range(1, 4):  # explosion_1 through explosion_3
            filename = f"explosion_{i}.wav"
            if self._sound_exists(filename):
                # Create multiple QSoundEffect instances for overlapping sounds
                for _ in range(2):  # 2 instances per sound for overlap
                    effect = QSoundEffect()
                    effect.setSource(self._get_sound_url(filename))
                    effect.setVolume(0.3)  # 30% volume
                    effect.setLoopCount(1)  # Play once
                    self.explosion_effects.append(effect)
                print(f"Loaded explosion sound effect: {filename}")

        # Load player hit sound
        if self._sound_exists("player_hit.wav"):
            self.player_hit_effect = QSoundEffect()
            self.player_hit_effect.setSource(self._get_sound_url("player_hit.wav"))
            self.player_hit_effect.setVolume(0.4)  # 40% volume
            self.player_hit_effect.setLoopCount(1)  # Play once
            print("Loaded player hit sound effect: player_hit.wav")

        # Load player hit 2 sound (for final hit)
        if self._sound_exists("player_hit_2.wav"):
            self.player_hit_2_effect = QSoundEffect()
            self.player_hit_2_effect.setSource(self._get_sound_url("player_hit_2.wav"))
            self.player_hit_2_effect.setVolume(0.5)  # 50% volume - more dramatic
            self.player_hit_2_effect.setLoopCount(1)  # Play once
            print("Loaded player hit 2 sound effect: player_hit_2.wav")

        # Load whoosh sounds for wave transitions
        if self._sound_exists("whoosh_1.wav"):
            self.whoosh_1_effect = QSoundEffect()
            self.whoosh_1_effect.setSource(self._get_sound_url("whoosh_1.wav"))
            self.whoosh_1_effect.setVolume(0.5)  # 50% volume
            self.whoosh_1_effect.setLoopCount(1)  # Play once
            print("Loaded whoosh 1 sound effect: whoosh_1.wav")

        if self._sound_exists("whoosh_2.wav"):
            self.whoosh_2_effect = QSoundEffect()
            self.whoosh_2_effect.setSource(self._get_sound_url("whoosh_2.wav"))
            self.whoosh_2_effect.setVolume(0.5)  # 50% volume
            self.whoosh_2_effect.setLoopCount(1)  # Play once
            print("Loaded whoosh 2 sound effect: whoosh_2.wav")

        # Load denied sounds for shield blocks and wrong keys
        if self._sound_exists("denied_1.wav"):
            self.denied_1_effect = QSoundEffect()
            self.denied_1_effect.setSource(self._get_sound_url("denied_1.wav"))
            self.denied_1_effect.setVolume(0.6)
            self.denied_1_effect.setLoopCount(1)  # Play once
            print("Loaded denied 1 sound effect: denied_1.wav")

        if self._sound_exists("denied_2.wav"):
            self.denied_2_effect = QSoundEffect()
            self.denied_2_effect.setSource(self._get_sound_url("denied_2.wav"))
            self.denied_2_effect.setVolume(0.6)
            self.denied_2_effect.setLoopCount(1)  # Play once
            print("Loaded denied 2 sound effect: denied_2.wav")

        if self._sound_exists("disablecone.wav"):
            self.disable_cone_effect = QSoundEffect()
            self.disable_cone_effect.setSource(self._get_sound_url("disablecone.wav"))
            self.disable_cone_effect.setVolume(1.0)
            self.disable_cone_effect.setLoopCount(1)  # Play once
            print("Loaded disable cone sound effect: disablecone.wav")

        if self._sound_exists("firecone.wav"):
            self.fire_cone_effect = QSoundEffect()
            self.fire_cone_effect.setSource(self._get_sound_url("firecone.wav"))
            self.fire_cone_effect.setVolume(1.0)
            self.fire_cone_effect.setLoopCount(1)  # Play once
            print("Loaded fire cone sound effect: firecone.wav")

        # Load twinkle sound effect for game start/restart
        if self._sound_exists("twinkle.wav"):
            self.twinkle_effect = QSoundEffect()
            self.twinkle_effect.setSource(self._get_sound_url("twinkle.wav"))
            self.twinkle_effect.setVolume(1.0)  # 60% volume - distinct but not too loud
            self.twinkle_effect.setLoopCount(1)  # Play once
            print("Loaded twinkle sound effect: twinkle.wav")
        else:
            print("Twinkle sound file NOT found: twinkle.wav")

        # Load thunder sound effect for boss entry flashes
        if self._sound_exists("thunder_1.wav"):
            self.thunder_effect = QSoundEffect()
            self.thunder_effect.setSource(self._get_sound_url("thunder_1.wav"))
            self.thunder_effect.setVolume(0.7)  # 70% volume - dramatic
            self.thunder_effect.setLoopCount(1)  # Play once
            print("Loaded thunder sound effect: thunder_1.wav")

        # Load you win music (using QMediaPlayer for MP3 support)
        if self._sound_exists("youwin.mp3"):
            self.youwin_playlist = QMediaPlaylist()
            self.youwin_playlist.addMedia(QMediaContent(self._get_sound_url("youwin.mp3")))
            self.youwin_playlist.setPlaybackMode(QMediaPlaylist.Loop)
            self.youwin_player.setPlaylist(self.youwin_playlist)
            self.youwin_player.setVolume(30)
            self.youwin_music_loaded = True
            print("Loaded you win music: youwin.mp3")
        else:
            print("You win music file NOT found: youwin.mp3")

        # Load minor scale sounds for intro screen key presses
        minor_scale_files = [
            "minor_scale_shifted_0_-5st.wav",
            "minor_scale_shifted_1_-3st.wav",
            "minor_scale_shifted_2_-2st.wav",
            "minor_scale_shifted_3_+0st.wav",
            "minor_scale_shifted_5_+3st.wav",
            "minor_scale_shifted_6_+5st.wav",
            "minor_scale_shifted_7_+7st.wav",
        ]
        for filename in minor_scale_files:
            if self._sound_exists(filename):
                effect = QSoundEffect()
                effect.setSource(self._get_sound_url(filename))
                effect.setVolume(0.3)  # 50% volume
                effect.setLoopCount(1)
                self.minor_scale_effects.append(effect)
        if self.minor_scale_effects:
            print(f"Loaded {len(self.minor_scale_effects)} minor scale sound effects")

        # Load background music (MP3 preferred for music) - gapless looping setup
        if self._sound_exists("spacedebris-loop.mp3"):
            self.music_file_url = self._get_sound_url("spacedebris-loop.mp3")
            self.music_volume = 25

            # Set up both players with the same media
            self.music_player_a.setMedia(QMediaContent(self.music_file_url))
            self.music_player_b.setMedia(QMediaContent(self.music_file_url))
            self.music_player_a.setVolume(self.music_volume)
            self.music_player_b.setVolume(0)  # Start silent

            # Get duration when media is loaded
            self.music_player_a.durationChanged.connect(self._on_music_duration_changed)

            # Set up loop check timer
            self.music_loop_check_timer = QTimer()
            self.music_loop_check_timer.timeout.connect(self._check_music_loop)

            print("Loaded background music (gapless): spacedebris-loop.mp3")
        else:
            print("No background music file found")

        # Load game over music (with looping playlist)
        if self._sound_exists("gameover.mp3"):
            self.gameover_playlist = QMediaPlaylist()
            self.gameover_playlist.addMedia(QMediaContent(self._get_sound_url("gameover.mp3")))
            self.gameover_playlist.setPlaybackMode(QMediaPlaylist.Loop)
            self.gameover_player.setPlaylist(self.gameover_playlist)
            self.gameover_player.setVolume(100)
            self.gameover_music_loaded = True
            print("Loaded game over music: gameover.mp3")
        else:
            print("No game over music file found")

    def _on_music_duration_changed(self, duration):
        """Called when music duration is known."""
        if duration > 0:
            self.music_duration = duration
            print(f"Background music duration: {duration}ms")

    def _check_music_loop(self):
        """Check if we need to start the next player for gapless loop."""
        if not self.music_duration:
            return

        current_pos = self.music_player.position()
        # Start next player when we're near the end (500ms before)
        loop_trigger_point = self.music_duration - 500

        if loop_trigger_point <= current_pos < self.music_duration:
            # Determine which player is next
            next_player = (
                self.music_player_b
                if self.music_player == self.music_player_a
                else self.music_player_a
            )

            # Only start if next player isn't already playing
            if next_player.state() != QMediaPlayer.PlayingState:
                next_player.setPosition(0)
                next_player.setVolume(self.music_volume)
                next_player.play()

                # Fade out current player
                self.music_player.setVolume(0)

                # Switch active player reference
                self.music_player = next_player
                print("Gapless loop: switched to next player")

    def play_background_music(self):
        """Start background music with gapless looping."""
        if not self.enabled or not self.music_file_url:
            return

        self.music_player = self.music_player_a
        self.music_player_a.setVolume(self.music_volume)
        self.music_player_a.setPosition(0)
        self.music_player_a.play()

        # Start the loop check timer (check every 100ms)
        if self.music_loop_check_timer:
            self.music_loop_check_timer.start(100)

        print("Background music started (gapless)")

    def stop_background_music(self):
        """Stop background music."""
        if self.music_loop_check_timer:
            self.music_loop_check_timer.stop()
        self.music_player_a.stop()
        self.music_player_b.stop()
        print("Background music stopped")

    def pause_background_music(self):
        """Pause background music."""
        if self.music_loop_check_timer:
            self.music_loop_check_timer.stop()
        self.music_player_a.pause()
        self.music_player_b.pause()

    def resume_background_music(self):
        """Resume background music."""
        if not self.enabled:
            return
        self.music_player.play()
        if self.music_loop_check_timer:
            self.music_loop_check_timer.start(100)

    def play_laser_sound(self):
        """Play a random laser sound effect."""
        if not self.enabled or not self.laser_effects:
            return

        # Use round-robin to select an effect instance
        effect = self.laser_effects[self.laser_index]
        self.laser_index = (self.laser_index + 1) % len(self.laser_effects)

        # QSoundEffect can play immediately even if already playing
        # It will mix/overlap automatically
        effect.play()

    def play_explosion_sound(self, volume: float = 0.3):
        """Play a random explosion sound effect.

        Args:
            volume: Volume level from 0.0 to 1.0 (default 0.3)
        """
        if not self.enabled or not self.explosion_effects:
            return

        # Use round-robin to select an effect instance
        effect = self.explosion_effects[self.explosion_index]
        self.explosion_index = (self.explosion_index + 1) % len(self.explosion_effects)

        # Set volume and play
        effect.setVolume(volume)
        effect.play()

    def play_player_hit_sound(self):
        """Play the player hit sound effect."""
        if not self.enabled or not self.player_hit_effect:
            return

        self.player_hit_effect.play()

    def play_player_hit_2_sound(self):
        """Play the final player hit sound effect (for death)."""
        if not self.enabled or not self.player_hit_2_effect:
            return

        self.player_hit_2_effect.play()

    def play_whoosh_1_sound(self):
        """Play whoosh sound for wave transition start."""
        if not self.enabled or not self.whoosh_1_effect:
            return

        self.whoosh_1_effect.play()

    def play_whoosh_2_sound(self):
        """Play whoosh sound for wave transition end."""
        if not self.enabled or not self.whoosh_2_effect:
            return

        self.whoosh_2_effect.play()

    def play_denied_1_sound(self):
        """Play denied sound for shield blocks."""
        if not self.enabled or not self.denied_1_effect:
            return

        self.denied_1_effect.play()

    def play_denied_2_sound(self):
        """Play denied sound for wrong keys."""
        if not self.enabled or not self.denied_2_effect:
            return

        self.denied_2_effect.play()

    def play_disable_cone_sound(self):
        if not self.enabled or not self.disable_cone_effect:
            return
        self.disable_cone_effect.play()

    def play_fire_cone_sound(self):
        if not self.enabled or not self.fire_cone_effect:
            return
        self.fire_cone_effect.play()

    def play_twinkle_sound(self):
        """Play the twinkle sound effect."""
        if not self.enabled or not self.twinkle_effect:
            print("Twinkle sound not played: disabled or effect not loaded.")
            return
        print("Playing twinkle sound.")
        self.twinkle_effect.play()

    def play_thunder_sound(self):
        """Play the thunder sound effect for boss entry flashes."""
        if not self.enabled or not self.thunder_effect:
            return
        self.thunder_effect.play()

    def play_you_win_sound(self):
        """Play the you win victory music."""
        if not self.enabled or not self.youwin_music_loaded:
            print("You win music not played: disabled or not loaded.")
            return
        print("Playing you win music.")
        self.youwin_player.play()

    def stop_you_win_sound(self):
        """Stop you win music."""
        self.youwin_player.stop()
        print("You win music stopped")

    def fade_out_you_win_music(self, duration: float = 3.0):
        """Fade out you win music over specified duration."""
        if not self.youwin_music_loaded:
            return

        # Setup fade parameters for you win music
        self.youwin_fade_start = self.youwin_player.volume()
        self.youwin_fade_target = 0
        self.youwin_fade_duration = duration
        self.youwin_fade_elapsed = 0

        if not self.youwin_fade_timer:
            self.youwin_fade_timer = QTimer()
            self.youwin_fade_timer.timeout.connect(self._update_youwin_fade)

        self.youwin_fade_timer.start(50)
        print(f"Starting you win music fade out over {duration}s")

    def _update_youwin_fade(self):
        """Update you win music fade effect."""
        self.youwin_fade_elapsed += 0.05

        if self.youwin_fade_elapsed >= self.youwin_fade_duration:
            self.youwin_player.setVolume(int(self.youwin_fade_target))
            self.youwin_fade_timer.stop()

            if self.youwin_fade_target == 0:
                self.youwin_player.stop()
            print("You win music fade complete")
        else:
            progress = self.youwin_fade_elapsed / self.youwin_fade_duration
            current_volume = (
                self.youwin_fade_start
                + (self.youwin_fade_target - self.youwin_fade_start) * progress
            )
            self.youwin_player.setVolume(int(current_volume))

    def play_minor_scale_sound(self):
        """Play the next minor scale sound in sequence (for intro screen key presses)."""
        if not self.enabled or not self.minor_scale_effects:
            return
        # randomize index
        self.minor_scale_index = random.randint(0, len(self.minor_scale_effects) - 1)
        effect = self.minor_scale_effects[self.minor_scale_index]
        effect.play()

    def set_enabled(self, enabled: bool):
        """Enable or disable sound."""
        self.enabled = enabled

        if not self.enabled:
            self.stop_background_music()
            # Stop all sound effects
            for effect in self.laser_effects:
                effect.stop()
            for effect in self.explosion_effects:
                effect.stop()
            if self.player_hit_effect:
                self.player_hit_effect.stop()
            if self.whoosh_1_effect:
                self.whoosh_1_effect.stop()
            if self.whoosh_2_effect:
                self.whoosh_2_effect.stop()
            if self.denied_1_effect:
                self.denied_1_effect.stop()
            if self.denied_2_effect:
                self.denied_2_effect.stop()
            if self.twinkle_effect:
                self.twinkle_effect.stop()
            if self.thunder_effect:
                self.thunder_effect.stop()

    def set_music_volume(self, volume: int):
        """Set background music volume (0-100)."""
        self.music_player.setVolume(volume)

    def set_effects_volume(self, volume: int):
        """Set sound effects volume (0-100)."""
        volume_float = volume / 100.0
        for effect in self.laser_effects:
            effect.setVolume(volume_float)
        for effect in self.explosion_effects:
            effect.setVolume(volume_float)
        if self.player_hit_effect:
            self.player_hit_effect.setVolume(volume_float)
        if self.whoosh_1_effect:
            self.whoosh_1_effect.setVolume(volume_float)
        if self.whoosh_2_effect:
            self.whoosh_2_effect.setVolume(volume_float)
        if self.denied_1_effect:
            self.denied_1_effect.setVolume(volume_float)
        if self.denied_2_effect:
            self.denied_2_effect.setVolume(volume_float)

    def is_music_playing(self) -> bool:
        """Check if background music is playing."""
        return (
            self.music_player_a.state() == QMediaPlayer.PlayingState
            or self.music_player_b.state() == QMediaPlayer.PlayingState
        )

    def play_gameover_music(self):
        """Start game over music."""
        if not self.enabled or not self.gameover_music_loaded:
            return

        self.gameover_player.play()
        print("Game over music started")

    def stop_gameover_music(self):
        """Stop game over music."""
        self.gameover_player.stop()
        print("Game over music stopped")

    def fade_out_background_music(self, duration: float = 1.0):
        """Fade out background music over specified duration."""
        if not self.is_music_playing():
            return

        # Setup fade parameters
        self.fade_start_volume = self.music_player.volume()
        self.fade_target_volume = 0
        self.fade_duration = duration
        self.fade_elapsed = 0

        # Create fade timer if it doesn't exist
        if not self.fade_timer:
            self.fade_timer = QTimer()
            self.fade_timer.timeout.connect(self._update_fade)

        # Start fade timer (update every 50ms)
        self.fade_timer.start(50)
        print(f"Starting background music fade out over {duration}s")

    def fade_in_background_music(self, target_volume: int = 15, duration: float = 1.0):
        """Fade in background music over specified duration."""
        # Setup fade parameters
        self.music_volume = 0
        self.music_player.setVolume(0)  # Start from silence
        self.play_background_music()  # Start playing if not already

        self.fade_start_volume = 0
        self.fade_target_volume = target_volume
        self.fade_duration = duration
        self.fade_elapsed = 0

        # Create fade timer if it doesn't exist
        if not self.fade_timer:
            self.fade_timer = QTimer()
            self.fade_timer.timeout.connect(self._update_fade)

        # Start fade timer (update every 50ms)
        self.fade_timer.start(50)
        print(f"Starting background music fade in to {target_volume} over {duration}s")

    def fade_music_for_pause(self, duration: float = 0.3):
        """Fade music to 10% volume for pause, remembering current volume."""
        self._pause_premute_volume = self.music_player.volume()
        if not self.fade_timer:
            self.fade_timer = QTimer()
            self.fade_timer.timeout.connect(self._update_fade)
        self.fade_start_volume = self._pause_premute_volume
        self.fade_target_volume = 10
        self.fade_duration = duration
        self.fade_elapsed = 0
        self.fade_timer.start(50)

    def fade_music_for_unpause(self, duration: float = 0.3):
        """Fade music back to pre-pause volume."""
        target = self._pause_premute_volume if self._pause_premute_volume is not None else 25
        if not self.fade_timer:
            self.fade_timer = QTimer()
            self.fade_timer.timeout.connect(self._update_fade)
        self.fade_start_volume = self.music_player.volume()
        self.fade_target_volume = target
        self.fade_duration = duration
        self.fade_elapsed = 0
        self.fade_timer.start(50)

    def crossfade_to_background_music(self, duration: float = 1.0):
        """Crossfade from game over or you win music to background music."""
        # Start fading in background music
        self.fade_in_background_music(15, duration)

        # Stop game over and you win music after duration
        QTimer.singleShot(int(duration * 1000), self.stop_gameover_music)
        QTimer.singleShot(int(duration * 1000), self.stop_you_win_sound)

    def _update_fade(self):
        """Update fade effect."""
        self.fade_elapsed += 0.05  # 50ms update interval

        if self.fade_elapsed >= self.fade_duration:
            # Fade complete
            self.music_volume = int(self.fade_target_volume)
            self.music_player.setVolume(self.music_volume)
            self.fade_timer.stop()

            # If we faded out completely, stop the music
            if self.fade_target_volume == 0:
                self.stop_background_music()

            print(f"Fade complete. Volume: {self.fade_target_volume}")
        else:
            # Calculate interpolated volume
            progress = self.fade_elapsed / self.fade_duration
            current_volume = int(
                self.fade_start_volume
                + (self.fade_target_volume - self.fade_start_volume) * progress
            )
            self.music_volume = current_volume
            self.music_player.setVolume(current_volume)
