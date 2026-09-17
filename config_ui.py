"""Configuration UI."""

from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QCheckBox,
    QPushButton,
    QGroupBox,
    QSpinBox,
    QScrollArea,
    QComboBox,
)
from PyQt5.QtCore import Qt, pyqtSignal


class ConfigUI(QMainWindow):
    """Configuration UI window for the game."""

    # Signals
    config_changed = pyqtSignal()
    restart_requested = pyqtSignal()

    def __init__(self, game_engine):
        super().__init__()
        self.game_engine = game_engine
        self.config = game_engine.config if game_engine else None

        self.setWindowTitle("Space Debris Configuration")

        if self.config:
            self._setup_ui()
            self._connect_signals()
            self._update_from_config()

        # Start hidden
        self.hide()

    def _setup_ui(self):
        """Set up the UI layout and controls."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Create scroll area for better organization
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(10, 10, 10, 10)

        # Enemy Spawning Group
        spawning_group = self._create_spawning_group()
        scroll_layout.addWidget(spawning_group)

        # Two-column layout for Wave Control and Gameplay
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(15)

        # Left column
        left_column = QVBoxLayout()
        wave_group = self._create_wave_group()
        left_column.addWidget(wave_group)
        left_column.addStretch()

        # Right column
        right_column = QVBoxLayout()
        gameplay_group = self._create_gameplay_group()
        right_column.addWidget(gameplay_group)
        right_column.addStretch()

        middle_layout.addLayout(left_column)
        middle_layout.addLayout(right_column)
        scroll_layout.addLayout(middle_layout)

        # Visual Effects Group (full width)
        effects_group = self._create_effects_group()
        scroll_layout.addWidget(effects_group)

        # Set up scroll area
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)

        # Action Buttons at bottom
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self.restart_btn = QPushButton("Restart Game")
        self.restart_btn.setMinimumHeight(35)
        self.restart_btn.clicked.connect(self.restart_requested.emit)

        self.reset_btn = QPushButton("Reset Config")
        self.reset_btn.setMinimumHeight(35)
        self.reset_btn.clicked.connect(self._reset_config)

        self.test_you_win_btn = QPushButton("Test You Win")
        self.test_you_win_btn.setMinimumHeight(35)
        self.test_you_win_btn.clicked.connect(self._test_you_win)

        self.close_btn = QPushButton("Close")
        self.close_btn.setMinimumHeight(35)
        self.close_btn.clicked.connect(self.hide)

        buttons_layout.addWidget(self.restart_btn)
        buttons_layout.addWidget(self.reset_btn)
        buttons_layout.addWidget(self.test_you_win_btn)
        buttons_layout.addWidget(self.close_btn)

        main_layout.addLayout(buttons_layout)

    def _create_spawning_group(self):
        """Create enemy spawning controls."""
        group = QGroupBox("Enemy Spawning")
        main_layout = QVBoxLayout(group)
        main_layout.setSpacing(12)

        # Single enemy type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Test Enemy Type:"))

        self.enemy_type_combo = QComboBox()
        self.enemy_type_combo.addItem("Normal Spawning", "")
        self.enemy_type_combo.addItem("Normal Only", "normal")
        self.enemy_type_combo.addItem("Rapid-Hit Only", "rapid_hit")
        self.enemy_type_combo.addItem("Pairs Only", "pair")
        self.enemy_type_combo.addItem("Reverse Only", "reverse")
        self.enemy_type_combo.addItem("Shielded Only", "shielded")
        self.enemy_type_combo.setMinimumHeight(30)
        type_layout.addWidget(self.enemy_type_combo)

        main_layout.addLayout(type_layout)

        return group

    def _create_wave_group(self):
        """Create wave control group."""
        group = QGroupBox("Wave Control")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Wave progression toggle
        self.wave_progression_cb = QCheckBox("Enable Wave Progression")
        self.wave_progression_cb.setChecked(self.config.spawning.enable_wave_progression)
        layout.addWidget(self.wave_progression_cb)

        # Force wave number
        wave_layout = QHBoxLayout()
        wave_layout.addWidget(QLabel("Force Wave:"))

        self.force_wave_spin = QSpinBox()
        self.force_wave_spin.setRange(-1, 20)
        self.force_wave_spin.setValue(self.config.spawning.force_wave_number)
        self.force_wave_spin.setSpecialValueText("Normal Progression")
        self.force_wave_spin.setMinimumHeight(25)
        wave_layout.addWidget(self.force_wave_spin)
        wave_layout.addStretch()

        layout.addLayout(wave_layout)

        return group

    def _create_gameplay_group(self):
        """Create gameplay modifiers group."""
        group = QGroupBox("Gameplay Modifiers")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Infinite health
        self.infinite_health_cb = QCheckBox("Infinite Health")
        self.infinite_health_cb.setChecked(self.config.spawning.infinite_health)
        layout.addWidget(self.infinite_health_cb)

        # Boss every wave
        self.boss_every_wave_cb = QCheckBox("Boss Every Wave")
        self.boss_every_wave_cb.setChecked(self.config.spawning.boss_every_wave)
        layout.addWidget(self.boss_every_wave_cb)

        self.boss_selection_combo = QComboBox()
        self.boss_selection_combo.addItem("Random (Normal)", "random")
        self.boss_selection_combo.addItem("Phase Shift", "phase_shift")
        self.boss_selection_combo.addItem("Force Field", "force_field")
        self.boss_selection_combo.addItem("Sinusoid", "sinusoid")
        self.boss_selection_combo.addItem("Chaotic Cloud", "chaotic_cloud")
        self.boss_selection_combo.addItem("Face", "face")
        self.boss_selection_combo.setMinimumHeight(25)
        layout.addWidget(self.boss_selection_combo)

        # Speed override checkbox and slider
        speed_layout = QHBoxLayout()
        self.speed_override_checkbox = QCheckBox("Speed Override:")
        self.speed_override_checkbox.setChecked(self.config.spawning.speed_override_enabled)
        speed_layout.addWidget(self.speed_override_checkbox)

        self.speed_slider = self._create_slider(
            0.1, 3.0, 0.1, self.config.spawning.speed_multiplier
        )
        self.speed_slider.setEnabled(self.config.spawning.speed_override_enabled)
        speed_layout.addWidget(self.speed_slider)

        self.speed_label = QLabel(f"{self.config.spawning.speed_multiplier:.1f}x")
        self.speed_label.setMinimumWidth(40)
        speed_layout.addWidget(self.speed_label)
        layout.addLayout(speed_layout)

        return group

    def _set_boss_combo_from_config(self):
        """Set boss combo box selection based on current config."""
        if self.config.spawning.test_phase_shift_boss:
            self.boss_selection_combo.setCurrentIndex(1)
        elif self.config.spawning.test_force_field_boss:
            self.boss_selection_combo.setCurrentIndex(2)
        elif self.config.spawning.test_sinusoid_boss:
            self.boss_selection_combo.setCurrentIndex(3)
        elif self.config.spawning.test_chaotic_cloud_boss:
            self.boss_selection_combo.setCurrentIndex(4)
        elif self.config.spawning.test_face_boss:
            self.boss_selection_combo.setCurrentIndex(5)
        else:
            self.boss_selection_combo.setCurrentIndex(0)

    def _apply_boss_selection(self):
        """Apply boss selection from combo box to config."""
        # Clear all boss test flags
        self.config.spawning.test_phase_shift_boss = False
        self.config.spawning.test_force_field_boss = False
        self.config.spawning.test_sinusoid_boss = False
        self.config.spawning.test_chaotic_cloud_boss = False
        self.config.spawning.test_face_boss = False

        # Set the selected boss test flag
        selection = self.boss_selection_combo.currentData()
        if selection == "phase_shift":
            self.config.spawning.test_phase_shift_boss = True
        elif selection == "force_field":
            self.config.spawning.test_force_field_boss = True
        elif selection == "sinusoid":
            self.config.spawning.test_sinusoid_boss = True
        elif selection == "chaotic_cloud":
            self.config.spawning.test_chaotic_cloud_boss = True
        elif selection == "face":
            self.config.spawning.test_face_boss = True

    def _create_effects_group(self):
        """Create visual effects group."""
        group = QGroupBox("Visual Effects")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Effect toggles in a grid
        toggles_layout = QHBoxLayout()
        toggles_layout.setSpacing(15)

        self.explosions_cb = QCheckBox("Explosions")
        self.explosions_cb.setChecked(self.config.visual_effects.explosions_enabled)
        toggles_layout.addWidget(self.explosions_cb)

        self.lasers_cb = QCheckBox("Lasers")
        self.lasers_cb.setChecked(self.config.visual_effects.lasers_enabled)
        toggles_layout.addWidget(self.lasers_cb)

        self.shake_cb = QCheckBox("Screen Shake")
        self.shake_cb.setChecked(self.config.visual_effects.screen_shake_enabled)
        toggles_layout.addWidget(self.shake_cb)

        self.show_fps_cb = QCheckBox("Show FPS")
        self.show_fps_cb.setChecked(self.config.visual_effects.show_fps)
        toggles_layout.addWidget(self.show_fps_cb)

        toggles_layout.addStretch()
        layout.addLayout(toggles_layout)

        # Effect intensity sliders
        intensity_label = QLabel("Effect Intensity:")
        intensity_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(intensity_label)

        self.explosion_intensity_slider = self._create_slider(
            0.1, 2.0, 0.1, self.config.visual_effects.explosion_size_multiplier
        )
        layout.addLayout(
            self._create_slider_layout("Explosion Size:", self.explosion_intensity_slider)
        )

        self.shake_intensity_slider = self._create_slider(
            0.1, 2.0, 0.1, self.config.visual_effects.shake_intensity_multiplier
        )
        layout.addLayout(
            self._create_slider_layout("Shake Intensity:", self.shake_intensity_slider)
        )

        return group

    def _create_slider(self, min_val, max_val, step, initial_val):
        """Create a slider with the given parameters."""
        slider = QSlider(Qt.Horizontal)
        slider.setRange(int(min_val / step), int(max_val / step))
        slider.setValue(int(initial_val / step))
        return slider

    def _create_slider_layout(self, label, slider):
        """Create a horizontal layout with label and slider."""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        # Label
        label_widget = QLabel(label)
        label_widget.setMinimumWidth(100)
        layout.addWidget(label_widget)

        # Slider
        slider.setMinimumWidth(150)
        layout.addWidget(slider, 1)

        # Value label
        value_label = QLabel("0.0")
        value_label.setMinimumWidth(35)
        value_label.setAlignment(Qt.AlignRight)
        layout.addWidget(value_label)

        # Connect slider to update value label
        def update_label():
            value = slider.value() * 0.1  # Step size
            value_label.setText(f"{value:.1f}")

        slider.valueChanged.connect(update_label)
        update_label()  # Set initial value

        return layout

    def _connect_signals(self):
        """Connect all UI signals to handlers."""
        # Enemy type selection
        self.enemy_type_combo.currentIndexChanged.connect(self._on_config_changed)

        # Wave control
        self.wave_progression_cb.toggled.connect(self._on_config_changed)
        self.force_wave_spin.valueChanged.connect(self._on_config_changed)

        # Gameplay modifiers
        self.infinite_health_cb.toggled.connect(self._on_config_changed)
        self.boss_every_wave_cb.toggled.connect(self._on_config_changed)
        self.boss_selection_combo.currentIndexChanged.connect(self._on_config_changed)
        self.speed_override_checkbox.toggled.connect(self._on_speed_override_toggled)
        self.speed_slider.valueChanged.connect(self._on_config_changed)

        # Visual effects
        self.explosions_cb.toggled.connect(self._on_config_changed)
        self.lasers_cb.toggled.connect(self._on_config_changed)
        self.shake_cb.toggled.connect(self._on_config_changed)
        self.show_fps_cb.toggled.connect(self._on_config_changed)
        self.explosion_intensity_slider.valueChanged.connect(self._on_config_changed)
        self.shake_intensity_slider.valueChanged.connect(self._on_config_changed)

    def _on_config_changed(self):
        """Handle configuration changes."""
        # Update config values from UI
        self.config.spawning.test_enemy_type = self.enemy_type_combo.currentData()

        self.config.spawning.enable_wave_progression = self.wave_progression_cb.isChecked()
        self.config.spawning.force_wave_number = self.force_wave_spin.value()

        self.config.spawning.infinite_health = self.infinite_health_cb.isChecked()
        self.config.spawning.boss_every_wave = self.boss_every_wave_cb.isChecked()
        self._apply_boss_selection()
        self.config.spawning.speed_override_enabled = self.speed_override_checkbox.isChecked()
        self.config.spawning.speed_multiplier = self.speed_slider.value() * 0.1
        self.speed_label.setText(f"{self.config.spawning.speed_multiplier:.1f}x")

        self.config.visual_effects.explosions_enabled = self.explosions_cb.isChecked()
        self.config.visual_effects.lasers_enabled = self.lasers_cb.isChecked()
        self.config.visual_effects.screen_shake_enabled = self.shake_cb.isChecked()
        self.config.visual_effects.show_fps = self.show_fps_cb.isChecked()
        self.config.visual_effects.explosion_size_multiplier = (
            self.explosion_intensity_slider.value() * 0.1
        )
        self.config.visual_effects.shake_intensity_multiplier = (
            self.shake_intensity_slider.value() * 0.1
        )

        # Apply speed changes immediately using effective speed
        effective_speed = self.config.spawning.get_effective_speed_multiplier()
        for enemy in self.game_engine.enemies:
            enemy.set_config_speed_multiplier(effective_speed)

        # Save config
        self.config.save()

        # Emit signal for any additional handling
        self.config_changed.emit()

    def _on_speed_override_toggled(self, enabled):
        """Handle speed override checkbox toggle."""
        self.speed_slider.setEnabled(enabled)
        self._on_config_changed()

    def _test_you_win(self):
        """Trigger the you win screen for testing."""
        if self.game_engine:
            self.game_engine.trigger_you_win_test()
            self.hide_ui()

    def _reset_config(self):
        """Reset configuration to defaults."""
        self.config.spawning.test_enemy_type = ""
        self.config.spawning.speed_override_enabled = False
        self.config.spawning.speed_multiplier = 1.0
        self.config.spawning.infinite_health = False
        self.config.spawning.boss_every_wave = False
        self.config.spawning.test_phase_shift_boss = False
        self.config.spawning.test_force_field_boss = False
        self.config.spawning.test_sinusoid_boss = False
        self.config.spawning.test_chaotic_cloud_boss = False
        self.config.spawning.test_face_boss = False
        self.config.spawning.enable_wave_progression = True
        self.config.spawning.force_wave_number = -1

        self.config.visual_effects.explosions_enabled = True
        self.config.visual_effects.lasers_enabled = True
        self.config.visual_effects.screen_shake_enabled = True
        self.config.visual_effects.show_fps = False
        self.config.visual_effects.explosion_size_multiplier = 1.0
        self.config.visual_effects.shake_intensity_multiplier = 1.0

        self.config.save()
        self._update_from_config()

    def _update_from_config(self):
        """Update UI from current config values."""
        # Update enemy type combo
        self._set_enemy_type_combo_from_config()

        self.wave_progression_cb.setChecked(self.config.spawning.enable_wave_progression)
        self.force_wave_spin.setValue(self.config.spawning.force_wave_number)

        self.infinite_health_cb.setChecked(self.config.spawning.infinite_health)
        self.boss_every_wave_cb.setChecked(self.config.spawning.boss_every_wave)
        self._set_boss_combo_from_config()
        self.speed_override_checkbox.setChecked(self.config.spawning.speed_override_enabled)
        self.speed_slider.setValue(int(self.config.spawning.speed_multiplier / 0.1))
        self.speed_slider.setEnabled(self.config.spawning.speed_override_enabled)
        self.speed_label.setText(f"{self.config.spawning.speed_multiplier:.1f}x")

        self.explosions_cb.setChecked(self.config.visual_effects.explosions_enabled)
        self.lasers_cb.setChecked(self.config.visual_effects.lasers_enabled)
        self.shake_cb.setChecked(self.config.visual_effects.screen_shake_enabled)
        self.show_fps_cb.setChecked(self.config.visual_effects.show_fps)
        self.explosion_intensity_slider.setValue(
            int(self.config.visual_effects.explosion_size_multiplier / 0.1)
        )
        self.shake_intensity_slider.setValue(
            int(self.config.visual_effects.shake_intensity_multiplier / 0.1)
        )

    def _set_enemy_type_combo_from_config(self):
        """Set enemy type combo box selection based on current config."""
        test_type = self.config.spawning.test_enemy_type
        for i in range(self.enemy_type_combo.count()):
            if self.enemy_type_combo.itemData(i) == test_type:
                self.enemy_type_combo.setCurrentIndex(i)
                return
        # Default to first item (Normal Spawning)
        self.enemy_type_combo.setCurrentIndex(0)

    def show_ui(self):
        """Show the configuration UI."""
        self._update_from_config()
        self.show()
        self.raise_()
        self.activateWindow()

    def hide_ui(self):
        """Hide the configuration UI."""
        self.hide()

    def toggle_ui(self):
        """Toggle UI visibility."""
        if self.isVisible():
            self.hide_ui()
        else:
            self.show_ui()
