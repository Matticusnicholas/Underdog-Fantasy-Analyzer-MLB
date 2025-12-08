"""
Draft screenshot OCR parser for extracting player information.
Supports Underdog, DraftKings, and similar fantasy platforms.
"""

import re
import os
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass

try:
    import pytesseract
    from PIL import Image
    import cv2
    import numpy as np
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from .preprocessor import ImagePreprocessor


@dataclass
class ParsedPlayer:
    """Represents a parsed player from screenshot."""
    name: str
    team: Optional[str] = None
    position: Optional[str] = None
    pick_number: Optional[int] = None
    round_number: Optional[int] = None
    salary: Optional[int] = None  # For DraftKings style
    confidence: float = 1.0  # OCR confidence score

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'team': self.team,
            'position': self.position,
            'pick_number': self.pick_number,
            'round_number': self.round_number,
            'salary': self.salary,
            'confidence': self.confidence
        }


class DraftScreenshotParser:
    """
    Parses draft screenshots to extract player information.

    Supports multiple formats:
    - Underdog Fantasy draft results
    - DraftKings lineup exports
    - Generic player lists
    """

    # MLB team abbreviations for detection
    MLB_TEAMS = {
        'NYY', 'BOS', 'TB', 'TOR', 'BAL',  # AL East
        'CLE', 'MIN', 'DET', 'KC', 'CWS', 'CHW',  # AL Central
        'HOU', 'TEX', 'SEA', 'LAA', 'OAK',  # AL West
        'ATL', 'PHI', 'NYM', 'MIA', 'WSH', 'WAS',  # NL East
        'MIL', 'CHC', 'CIN', 'PIT', 'STL',  # NL Central
        'LAD', 'SD', 'ARI', 'SF', 'COL',  # NL West
    }

    # Position abbreviations
    POSITIONS = {'P', 'SP', 'RP', 'C', '1B', '2B', 'SS', '3B', 'OF', 'LF', 'CF', 'RF', 'DH', 'UTIL'}

    def __init__(self, tesseract_path: str = None):
        """
        Initialize the parser.

        Args:
            tesseract_path: Optional path to tesseract executable
        """
        if not TESSERACT_AVAILABLE:
            raise ImportError(
                "OCR dependencies not installed. Run: pip install pytesseract pillow opencv-python"
            )

        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

        self.preprocessor = ImagePreprocessor()

        # Regex patterns for parsing
        self.patterns = {
            # Pattern: "1. Mike Trout OF LAA" or "1 Mike Trout OF LAA"
            'numbered_player': re.compile(
                r'(\d+)[.\s]+([A-Za-z\s\'\-\.]+?)\s+(' + '|'.join(self.POSITIONS) + r')\s+(' + '|'.join(self.MLB_TEAMS) + r')',
                re.IGNORECASE
            ),
            # Pattern: "Mike Trout - OF - LAA"
            'dashed_player': re.compile(
                r'([A-Za-z\s\'\-\.]+?)\s*[-–]\s*(' + '|'.join(self.POSITIONS) + r')\s*[-–]\s*(' + '|'.join(self.MLB_TEAMS) + r')',
                re.IGNORECASE
            ),
            # Pattern: "Mike Trout (LAA - OF)"
            'parenthetical': re.compile(
                r'([A-Za-z\s\'\-\.]+?)\s*\((' + '|'.join(self.MLB_TEAMS) + r')\s*[-–]\s*(' + '|'.join(self.POSITIONS) + r')\)',
                re.IGNORECASE
            ),
            # Pattern: Team then position "LAA OF Mike Trout"
            'team_first': re.compile(
                r'(' + '|'.join(self.MLB_TEAMS) + r')\s+(' + '|'.join(self.POSITIONS) + r')\s+([A-Za-z\s\'\-\.]+)',
                re.IGNORECASE
            ),
            # Simple name with team: "Mike Trout LAA"
            'name_team': re.compile(
                r'([A-Za-z][A-Za-z\s\'\-\.]+[a-z])\s+(' + '|'.join(self.MLB_TEAMS) + r')\b',
                re.IGNORECASE
            ),
            # Just a name (fallback)
            'name_only': re.compile(r'^([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*$'),
            # Salary pattern for DK: "$5,400"
            'salary': re.compile(r'\$?([\d,]+)'),
            # Round indicator: "Round 1" or "R1"
            'round': re.compile(r'(?:Round|R)\s*(\d+)', re.IGNORECASE),
        }

    def parse_screenshot(self, image_path: str,
                         platform: str = 'auto') -> List[ParsedPlayer]:
        """
        Parse a draft screenshot and extract players.

        Args:
            image_path: Path to screenshot image
            platform: Platform type ('underdog', 'draftkings', 'auto')

        Returns:
            List of ParsedPlayer objects
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Preprocess image
        processed = self.preprocessor.preprocess(image_path)

        # Run OCR
        text = self._run_ocr(processed)

        # Parse based on platform
        if platform == 'auto':
            platform = self._detect_platform(text)

        players = self._parse_text(text, platform)

        return players

    def parse_text(self, text: str, platform: str = 'auto') -> List[ParsedPlayer]:
        """
        Parse raw text input (for manual entry or copy/paste).

        Args:
            text: Raw text containing player information
            platform: Platform type

        Returns:
            List of ParsedPlayer objects
        """
        if platform == 'auto':
            platform = self._detect_platform(text)

        return self._parse_text(text, platform)

    def _run_ocr(self, image: np.ndarray, config: str = None) -> str:
        """Run Tesseract OCR on preprocessed image."""
        if config is None:
            # PSM 6: Assume uniform block of text
            # PSM 4: Assume single column of text
            config = '--psm 6 --oem 3'

        # Convert to PIL Image for pytesseract
        pil_image = Image.fromarray(image)

        text = pytesseract.image_to_string(pil_image, config=config)

        return text

    def _detect_platform(self, text: str) -> str:
        """Detect which platform the screenshot is from."""
        text_lower = text.lower()

        if 'underdog' in text_lower:
            return 'underdog'
        elif 'draftkings' in text_lower or 'dk' in text_lower:
            return 'draftkings'
        elif 'fanduel' in text_lower or 'fd' in text_lower:
            return 'fanduel'
        elif '$' in text and any(c.isdigit() for c in text):
            # Likely DFS with salaries
            return 'draftkings'

        return 'generic'

    def _parse_text(self, text: str, platform: str) -> List[ParsedPlayer]:
        """Parse text into players based on platform format."""
        lines = text.strip().split('\n')
        players = []
        current_round = 1
        pick_counter = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for round indicator
            round_match = self.patterns['round'].search(line)
            if round_match:
                current_round = int(round_match.group(1))
                continue

            # Try to parse player from line
            player = self._parse_line(line, platform)
            if player:
                pick_counter += 1
                player.round_number = current_round
                if player.pick_number is None:
                    player.pick_number = pick_counter
                players.append(player)

        return players

    def _parse_line(self, line: str, platform: str) -> Optional[ParsedPlayer]:
        """Parse a single line to extract player info."""
        # Clean up common OCR errors
        line = self._clean_ocr_text(line)

        # Try numbered pattern first (most common in draft results)
        match = self.patterns['numbered_player'].search(line)
        if match:
            return ParsedPlayer(
                name=self._clean_name(match.group(2)),
                position=match.group(3).upper(),
                team=self._normalize_team(match.group(4)),
                pick_number=int(match.group(1))
            )

        # Try dashed pattern
        match = self.patterns['dashed_player'].search(line)
        if match:
            return ParsedPlayer(
                name=self._clean_name(match.group(1)),
                position=match.group(2).upper(),
                team=self._normalize_team(match.group(3))
            )

        # Try parenthetical pattern
        match = self.patterns['parenthetical'].search(line)
        if match:
            return ParsedPlayer(
                name=self._clean_name(match.group(1)),
                team=self._normalize_team(match.group(2)),
                position=match.group(3).upper()
            )

        # Try team first pattern
        match = self.patterns['team_first'].search(line)
        if match:
            return ParsedPlayer(
                name=self._clean_name(match.group(3)),
                team=self._normalize_team(match.group(1)),
                position=match.group(2).upper()
            )

        # Try name with team
        match = self.patterns['name_team'].search(line)
        if match:
            name = self._clean_name(match.group(1))
            if len(name) > 3:  # Avoid false positives
                return ParsedPlayer(
                    name=name,
                    team=self._normalize_team(match.group(2))
                )

        # Fallback: try to extract just a name
        match = self.patterns['name_only'].match(line)
        if match:
            name = self._clean_name(match.group(1))
            if len(name) > 5:
                return ParsedPlayer(name=name, confidence=0.7)

        # Last resort: look for any recognizable player name pattern
        words = line.split()
        if len(words) >= 2:
            potential_name = ' '.join(words[:2])
            if self._looks_like_name(potential_name):
                player = ParsedPlayer(name=self._clean_name(potential_name), confidence=0.5)
                # Try to find team in rest of line
                for word in words[2:]:
                    if word.upper() in self.MLB_TEAMS:
                        player.team = self._normalize_team(word)
                        player.confidence = 0.7
                        break
                    elif word.upper() in self.POSITIONS:
                        player.position = word.upper()
                return player

        return None

    def _clean_ocr_text(self, text: str) -> str:
        """Clean common OCR errors."""
        replacements = {
            '|': 'I',
            '0': 'O',  # Only in specific contexts
            '1': 'I',  # Only in specific contexts
            '5': 'S',  # Only in specific contexts
            '  ': ' ',
        }

        # Only apply letter replacements in likely name contexts
        # For now, just fix spacing
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _clean_name(self, name: str) -> str:
        """Clean and normalize player name."""
        # Remove extra whitespace
        name = ' '.join(name.split())

        # Remove leading/trailing punctuation
        name = name.strip('.,- ')

        # Title case
        name = ' '.join(word.capitalize() for word in name.split())

        # Handle suffixes
        for suffix in [' Jr', ' Sr', ' Ii', ' Iii', ' Iv']:
            if name.endswith(suffix):
                name = name[:-len(suffix)] + suffix.replace(' ', ' ').upper()

        return name

    def _normalize_team(self, team: str) -> str:
        """Normalize team abbreviation."""
        team = team.upper().strip()

        # Handle common variations
        team_map = {
            'CHW': 'CWS',
            'WAS': 'WSH',
            'AZ': 'ARI',
            'KC': 'KC',
            'TB': 'TB',
            'SF': 'SF',
            'SD': 'SD',
        }

        return team_map.get(team, team)

    def _looks_like_name(self, text: str) -> bool:
        """Check if text looks like a player name."""
        parts = text.split()
        if len(parts) < 2:
            return False

        # Names typically have capitalized first letters
        for part in parts:
            if not part or not part[0].isupper():
                return False

        # Names shouldn't be all caps (likely OCR noise)
        if text.isupper():
            return False

        # Names shouldn't contain numbers
        if any(c.isdigit() for c in text):
            return False

        return True

    def get_ocr_confidence(self, image_path: str) -> Dict[str, Any]:
        """
        Get detailed OCR confidence data for an image.

        Returns dict with word-level confidence scores.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        processed = self.preprocessor.preprocess(image_path)
        pil_image = Image.fromarray(processed)

        # Get detailed OCR data
        data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT)

        words = []
        total_conf = 0
        valid_words = 0

        for i, word in enumerate(data['text']):
            if word.strip():
                conf = data['conf'][i]
                if conf > 0:  # -1 means no confidence available
                    words.append({
                        'text': word,
                        'confidence': conf,
                        'bbox': (data['left'][i], data['top'][i],
                                 data['width'][i], data['height'][i])
                    })
                    total_conf += conf
                    valid_words += 1

        avg_confidence = total_conf / valid_words if valid_words > 0 else 0

        return {
            'average_confidence': avg_confidence,
            'word_count': valid_words,
            'words': words
        }


def parse_manual_entry(text: str) -> List[ParsedPlayer]:
    """
    Convenience function to parse manually entered text.
    Useful when OCR isn't available or for copy/paste scenarios.
    """
    parser = DraftScreenshotParser()
    return parser.parse_text(text)
