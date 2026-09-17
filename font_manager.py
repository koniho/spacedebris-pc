"""Font management."""

from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtCore import Qt, QFile, QIODevice
import os


class FontManager:
    """Manages fonts for the game."""

    def __init__(self):
        """Initialize font manager."""
        self.fonts_loaded = False
        self.space_font_family = None
        self._initialized = False

    def _load_font_from_resource(self, resource_path: str, font_db: QFontDatabase) -> int:
        """Load font from Qt resource path using addApplicationFontFromData.

        Returns font_id or -1 on failure.
        """
        file = QFile(resource_path)
        if file.open(QIODevice.ReadOnly):
            font_data = file.readAll()
            file.close()
            return font_db.addApplicationFontFromData(font_data)
        return -1

    def load_fonts(self):
        """Load custom fonts and set up font hierarchy."""
        font_db = QFontDatabase()

        # Prioritize Orbitron fonts
        orbitron_files = [
            "orbitron-bold.otf",
            "orbitron-medium.otf",
            "orbitron-light.otf",
            "orbitron-black.otf",
        ]

        for font_file in orbitron_files:
            font_id = -1

            # Try Qt resource first (for bundled app)
            resource_path = f":/fonts/{font_file}"
            if QFile.exists(resource_path):
                font_id = self._load_font_from_resource(resource_path, font_db)
                if font_id != -1:
                    print(f"Loaded font from Qt resource: {resource_path}")

            if font_id == -1:
                # Fall back to filesystem (for development)
                fonts_dir = os.path.join(os.path.dirname(__file__), "fonts")
                font_path = os.path.join(fonts_dir, font_file)
                if os.path.exists(font_path):
                    font_id = font_db.addApplicationFont(font_path)

            if font_id != -1:
                families = font_db.applicationFontFamilies(font_id)
                if families and "Orbitron" in families[0]:
                    self.space_font_family = families[0]
                    self.fonts_loaded = True
                    print(f"Loaded Orbitron font: {self.space_font_family}")
                    return

        # Fallback to any other custom fonts in filesystem
        fonts_dir = os.path.join(os.path.dirname(__file__), "fonts")
        if os.path.exists(fonts_dir):
            for font_file in os.listdir(fonts_dir):
                if font_file.lower().endswith((".ttf", ".otf")):
                    font_path = os.path.join(fonts_dir, font_file)
                    font_id = font_db.addApplicationFont(font_path)
                    if font_id != -1:
                        families = font_db.applicationFontFamilies(font_id)
                        if families:
                            self.space_font_family = families[0]
                            self.fonts_loaded = True
                            print(f"Loaded custom font: {self.space_font_family}")
                            return

        # Fallback to system fonts with futuristic appearance
        available_families = font_db.families()

        # Priority order of space/sci-fi looking system fonts
        preferred_fonts = [
            "Orbitron",  # If Google Fonts Orbitron is installed
            "Courier New",  # Classic monospace, tech feel
            "Consolas",  # Microsoft's modern monospace
            "Monaco",  # Mac monospace
            "SF Mono",  # Apple's system monospace
            "Roboto Mono",  # Google's monospace
            "DejaVu Sans Mono",  # Common Linux monospace
            "Liberation Mono",  # Open source alternative
            "Menlo",  # Mac terminal font
            "Inconsolata",  # Popular programmer font
            "Source Code Pro",  # Adobe's monospace
        ]

        for font_name in preferred_fonts:
            if font_name in available_families:
                self.space_font_family = font_name
                print(f"Using system font: {font_name}")
                break

        if not self.space_font_family:
            # Ultimate fallback
            self.space_font_family = "monospace"
            print("Using fallback monospace font")

    def _ensure_initialized(self):
        """Ensure fonts are loaded when first accessed."""
        if not self._initialized:
            self.load_fonts()
            self._initialized = True

    def get_title_font(self, size=48, bold=True) -> QFont:
        """Get font for main titles."""
        self._ensure_initialized()
        font = QFont(self.space_font_family)
        font.setPixelSize(size)
        if bold:
            font.setBold(True)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 2)  # Add spacing for sci-fi feel
        return font

    def get_subtitle_font(self, size=18, bold=False) -> QFont:
        """Get font for subtitles."""
        self._ensure_initialized()
        font = QFont(self.space_font_family)
        font.setPixelSize(size)
        if bold:
            font.setBold(True)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 1)
        return font

    def get_button_font(self, size=20, bold=True) -> QFont:
        """Get font for button labels."""
        self._ensure_initialized()
        font = QFont(self.space_font_family)
        font.setPixelSize(size)
        if bold:
            font.setBold(True)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 1)
        return font

    def get_instruction_font(self, size=24, bold=False) -> QFont:
        """Get font for instruction text."""
        self._ensure_initialized()
        font = QFont(self.space_font_family)
        font.setPixelSize(size)
        if bold:
            font.setBold(True)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 1)
        return font

    def get_hud_font(self, size=16, bold=True) -> QFont:
        """Get font for HUD elements."""
        self._ensure_initialized()
        font = QFont(self.space_font_family)
        font.setPixelSize(size)
        if bold:
            font.setBold(True)
        return font

    def get_enemy_letter_font(self, size=20, bold=True) -> QFont:
        """Get font for enemy letters."""
        self._ensure_initialized()
        font = QFont(self.space_font_family)
        font.setPixelSize(size)
        if bold:
            font.setBold(True)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 1)
        return font


# Global font manager instance
font_manager = FontManager()
