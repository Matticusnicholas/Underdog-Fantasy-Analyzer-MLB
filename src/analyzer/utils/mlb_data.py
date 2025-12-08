"""
MLB reference data for teams and positions.
"""

from typing import Dict, List, Optional


class MLBTeams:
    """MLB team data and utilities."""

    TEAMS = {
        # AL East
        'NYY': {'name': 'New York Yankees', 'city': 'New York', 'division': 'AL East'},
        'BOS': {'name': 'Boston Red Sox', 'city': 'Boston', 'division': 'AL East'},
        'TB': {'name': 'Tampa Bay Rays', 'city': 'Tampa Bay', 'division': 'AL East'},
        'TOR': {'name': 'Toronto Blue Jays', 'city': 'Toronto', 'division': 'AL East'},
        'BAL': {'name': 'Baltimore Orioles', 'city': 'Baltimore', 'division': 'AL East'},

        # AL Central
        'CLE': {'name': 'Cleveland Guardians', 'city': 'Cleveland', 'division': 'AL Central'},
        'MIN': {'name': 'Minnesota Twins', 'city': 'Minnesota', 'division': 'AL Central'},
        'DET': {'name': 'Detroit Tigers', 'city': 'Detroit', 'division': 'AL Central'},
        'KC': {'name': 'Kansas City Royals', 'city': 'Kansas City', 'division': 'AL Central'},
        'CWS': {'name': 'Chicago White Sox', 'city': 'Chicago', 'division': 'AL Central'},

        # AL West
        'HOU': {'name': 'Houston Astros', 'city': 'Houston', 'division': 'AL West'},
        'TEX': {'name': 'Texas Rangers', 'city': 'Texas', 'division': 'AL West'},
        'SEA': {'name': 'Seattle Mariners', 'city': 'Seattle', 'division': 'AL West'},
        'LAA': {'name': 'Los Angeles Angels', 'city': 'Los Angeles', 'division': 'AL West'},
        'OAK': {'name': 'Oakland Athletics', 'city': 'Oakland', 'division': 'AL West'},

        # NL East
        'ATL': {'name': 'Atlanta Braves', 'city': 'Atlanta', 'division': 'NL East'},
        'PHI': {'name': 'Philadelphia Phillies', 'city': 'Philadelphia', 'division': 'NL East'},
        'NYM': {'name': 'New York Mets', 'city': 'New York', 'division': 'NL East'},
        'MIA': {'name': 'Miami Marlins', 'city': 'Miami', 'division': 'NL East'},
        'WSH': {'name': 'Washington Nationals', 'city': 'Washington', 'division': 'NL East'},

        # NL Central
        'MIL': {'name': 'Milwaukee Brewers', 'city': 'Milwaukee', 'division': 'NL Central'},
        'CHC': {'name': 'Chicago Cubs', 'city': 'Chicago', 'division': 'NL Central'},
        'CIN': {'name': 'Cincinnati Reds', 'city': 'Cincinnati', 'division': 'NL Central'},
        'PIT': {'name': 'Pittsburgh Pirates', 'city': 'Pittsburgh', 'division': 'NL Central'},
        'STL': {'name': 'St. Louis Cardinals', 'city': 'St. Louis', 'division': 'NL Central'},

        # NL West
        'LAD': {'name': 'Los Angeles Dodgers', 'city': 'Los Angeles', 'division': 'NL West'},
        'SD': {'name': 'San Diego Padres', 'city': 'San Diego', 'division': 'NL West'},
        'ARI': {'name': 'Arizona Diamondbacks', 'city': 'Arizona', 'division': 'NL West'},
        'SF': {'name': 'San Francisco Giants', 'city': 'San Francisco', 'division': 'NL West'},
        'COL': {'name': 'Colorado Rockies', 'city': 'Colorado', 'division': 'NL West'},
    }

    # Common aliases
    ALIASES = {
        'CHW': 'CWS',
        'WAS': 'WSH',
        'AZ': 'ARI',
        'TAM': 'TB',
        'KCR': 'KC',
        'SDP': 'SD',
        'SFG': 'SF',
        'LAA': 'LAA',
        'ANA': 'LAA',
    }

    @classmethod
    def get_all_abbreviations(cls) -> List[str]:
        """Get all team abbreviations."""
        return list(cls.TEAMS.keys())

    @classmethod
    def normalize_abbreviation(cls, abbr: str) -> str:
        """Normalize team abbreviation to standard form."""
        abbr = abbr.upper().strip()
        return cls.ALIASES.get(abbr, abbr)

    @classmethod
    def get_team_name(cls, abbr: str) -> Optional[str]:
        """Get full team name from abbreviation."""
        abbr = cls.normalize_abbreviation(abbr)
        team = cls.TEAMS.get(abbr)
        return team['name'] if team else None

    @classmethod
    def get_division(cls, abbr: str) -> Optional[str]:
        """Get team's division."""
        abbr = cls.normalize_abbreviation(abbr)
        team = cls.TEAMS.get(abbr)
        return team['division'] if team else None

    @classmethod
    def get_teams_by_division(cls, division: str) -> List[str]:
        """Get all team abbreviations in a division."""
        return [
            abbr for abbr, data in cls.TEAMS.items()
            if data['division'] == division
        ]

    @classmethod
    def is_valid_team(cls, abbr: str) -> bool:
        """Check if abbreviation is valid."""
        return cls.normalize_abbreviation(abbr) in cls.TEAMS


class MLBPositions:
    """MLB position data and utilities."""

    # All positions
    PITCHER = {'P', 'SP', 'RP'}
    CATCHER = {'C'}
    INFIELD = {'1B', '2B', 'SS', '3B'}
    OUTFIELD = {'OF', 'LF', 'CF', 'RF'}
    UTILITY = {'DH', 'UTIL'}

    ALL_POSITIONS = PITCHER | CATCHER | INFIELD | OUTFIELD | UTILITY

    # Position aliases
    ALIASES = {
        'PITCHER': 'P',
        'STARTING PITCHER': 'SP',
        'RELIEF PITCHER': 'RP',
        'CATCHER': 'C',
        'FIRST BASE': '1B',
        'SECOND BASE': '2B',
        'SHORTSTOP': 'SS',
        'THIRD BASE': '3B',
        'OUTFIELD': 'OF',
        'LEFT FIELD': 'LF',
        'CENTER FIELD': 'CF',
        'RIGHT FIELD': 'RF',
        'DESIGNATED HITTER': 'DH',
        'UTILITY': 'UTIL',
    }

    @classmethod
    def normalize_position(cls, pos: str) -> str:
        """Normalize position to standard abbreviation."""
        pos = pos.upper().strip()
        return cls.ALIASES.get(pos, pos)

    @classmethod
    def is_pitcher(cls, pos: str) -> bool:
        """Check if position is a pitcher."""
        return cls.normalize_position(pos) in cls.PITCHER

    @classmethod
    def is_hitter(cls, pos: str) -> bool:
        """Check if position is a hitter (non-pitcher)."""
        pos = cls.normalize_position(pos)
        return pos in (cls.CATCHER | cls.INFIELD | cls.OUTFIELD | cls.UTILITY)

    @classmethod
    def get_position_category(cls, pos: str) -> str:
        """Get position category (Pitcher, Catcher, Infield, Outfield, Utility)."""
        pos = cls.normalize_position(pos)

        if pos in cls.PITCHER:
            return 'Pitcher'
        elif pos in cls.CATCHER:
            return 'Catcher'
        elif pos in cls.INFIELD:
            return 'Infield'
        elif pos in cls.OUTFIELD:
            return 'Outfield'
        elif pos in cls.UTILITY:
            return 'Utility'
        else:
            return 'Unknown'

    @classmethod
    def is_valid_position(cls, pos: str) -> bool:
        """Check if position is valid."""
        return cls.normalize_position(pos) in cls.ALL_POSITIONS
