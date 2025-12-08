"""
Database manager for handling all database operations.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import sessionmaker, Session

from .models import (
    Base, Player, Team, DraftEntry, Contest,
    StackGroup, PlayerCorrelation, draft_entry_players
)


class DatabaseManager:
    """Manages all database operations for the Fantasy Analyzer."""

    def __init__(self, db_path: str = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file. Defaults to ./data/fantasy.db
        """
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                'data', 'fantasy.db'
            )

        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

        # Initialize MLB teams if empty
        self._init_mlb_teams()

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def _init_mlb_teams(self):
        """Initialize MLB teams reference data."""
        session = self.get_session()
        try:
            # Check if teams already exist
            if session.query(Team).count() > 0:
                return

            mlb_teams = [
                # AL East
                ("NYY", "New York Yankees", "New York", "AL East", "AL"),
                ("BOS", "Boston Red Sox", "Boston", "AL East", "AL"),
                ("TB", "Tampa Bay Rays", "Tampa Bay", "AL East", "AL"),
                ("TOR", "Toronto Blue Jays", "Toronto", "AL East", "AL"),
                ("BAL", "Baltimore Orioles", "Baltimore", "AL East", "AL"),
                # AL Central
                ("CLE", "Cleveland Guardians", "Cleveland", "AL Central", "AL"),
                ("MIN", "Minnesota Twins", "Minnesota", "AL Central", "AL"),
                ("DET", "Detroit Tigers", "Detroit", "AL Central", "AL"),
                ("KC", "Kansas City Royals", "Kansas City", "AL Central", "AL"),
                ("CWS", "Chicago White Sox", "Chicago", "AL Central", "AL"),
                # AL West
                ("HOU", "Houston Astros", "Houston", "AL West", "AL"),
                ("TEX", "Texas Rangers", "Texas", "AL West", "AL"),
                ("SEA", "Seattle Mariners", "Seattle", "AL West", "AL"),
                ("LAA", "Los Angeles Angels", "Los Angeles", "AL West", "AL"),
                ("OAK", "Oakland Athletics", "Oakland", "AL West", "AL"),
                # NL East
                ("ATL", "Atlanta Braves", "Atlanta", "NL East", "NL"),
                ("PHI", "Philadelphia Phillies", "Philadelphia", "NL East", "NL"),
                ("NYM", "New York Mets", "New York", "NL East", "NL"),
                ("MIA", "Miami Marlins", "Miami", "NL East", "NL"),
                ("WSH", "Washington Nationals", "Washington", "NL East", "NL"),
                # NL Central
                ("MIL", "Milwaukee Brewers", "Milwaukee", "NL Central", "NL"),
                ("CHC", "Chicago Cubs", "Chicago", "NL Central", "NL"),
                ("CIN", "Cincinnati Reds", "Cincinnati", "NL Central", "NL"),
                ("PIT", "Pittsburgh Pirates", "Pittsburgh", "NL Central", "NL"),
                ("STL", "St. Louis Cardinals", "St. Louis", "NL Central", "NL"),
                # NL West
                ("LAD", "Los Angeles Dodgers", "Los Angeles", "NL West", "NL"),
                ("SD", "San Diego Padres", "San Diego", "NL West", "NL"),
                ("ARI", "Arizona Diamondbacks", "Arizona", "NL West", "NL"),
                ("SF", "San Francisco Giants", "San Francisco", "NL West", "NL"),
                ("COL", "Colorado Rockies", "Colorado", "NL West", "NL"),
            ]

            for abbr, name, city, division, league in mlb_teams:
                team = Team(
                    abbreviation=abbr,
                    name=name,
                    city=city,
                    division=division,
                    league=league
                )
                session.add(team)

            session.commit()
        finally:
            session.close()

    # ==================== Player Operations ====================

    def add_player(self, name: str, mlb_team: str = None, position: str = None,
                   positions: str = None) -> Player:
        """Add a new player to the database."""
        session = self.get_session()
        try:
            normalized = self._normalize_name(name)

            # Check if player already exists
            existing = session.query(Player).filter(
                Player.normalized_name == normalized,
                Player.mlb_team == mlb_team
            ).first()

            if existing:
                return existing

            player = Player(
                name=name,
                normalized_name=normalized,
                mlb_team=mlb_team,
                position=position,
                positions=positions
            )
            session.add(player)
            session.commit()
            session.refresh(player)
            return player
        finally:
            session.close()

    def find_player(self, name: str, mlb_team: str = None) -> Optional[Player]:
        """Find a player by name (fuzzy matching)."""
        session = self.get_session()
        try:
            normalized = self._normalize_name(name)

            query = session.query(Player).filter(
                Player.normalized_name.like(f"%{normalized}%")
            )

            if mlb_team:
                query = query.filter(Player.mlb_team == mlb_team)

            return query.first()
        finally:
            session.close()

    def get_all_players(self) -> List[Player]:
        """Get all players from database."""
        session = self.get_session()
        try:
            return session.query(Player).all()
        finally:
            session.close()

    def get_or_create_player(self, name: str, mlb_team: str = None,
                             position: str = None) -> Player:
        """Get existing player or create new one."""
        player = self.find_player(name, mlb_team)
        if player:
            return player
        return self.add_player(name, mlb_team, position)

    # ==================== Contest Operations ====================

    def create_contest(self, name: str, platform: str = "Underdog",
                       contest_type: str = "Best Ball", entry_fee: float = 0.0) -> Contest:
        """Create a new contest."""
        session = self.get_session()
        try:
            contest = Contest(
                name=name,
                platform=platform,
                contest_type=contest_type,
                entry_fee=entry_fee
            )
            session.add(contest)
            session.commit()
            session.refresh(contest)
            return contest
        finally:
            session.close()

    def get_contest(self, contest_id: int) -> Optional[Contest]:
        """Get a contest by ID."""
        session = self.get_session()
        try:
            return session.query(Contest).filter(Contest.id == contest_id).first()
        finally:
            session.close()

    def get_all_contests(self) -> List[Contest]:
        """Get all contests."""
        session = self.get_session()
        try:
            return session.query(Contest).all()
        finally:
            session.close()

    # ==================== Draft Entry Operations ====================

    def create_draft_entry(self, player_names: List[str], contest_id: int = None,
                           entry_name: str = None, draft_position: int = None,
                           source_file: str = None, player_teams: List[str] = None,
                           player_positions: List[str] = None) -> DraftEntry:
        """
        Create a new draft entry with players.

        Args:
            player_names: List of player names in draft order
            contest_id: Optional contest ID
            entry_name: Optional name for this entry
            draft_position: Draft slot position
            source_file: Source screenshot file path
            player_teams: Optional list of MLB teams corresponding to players
            player_positions: Optional list of positions corresponding to players
        """
        session = self.get_session()
        try:
            entry = DraftEntry(
                entry_name=entry_name or f"Entry {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                contest_id=contest_id,
                draft_position=draft_position,
                total_picks=len(player_names),
                source_file=source_file,
                source_type='screenshot' if source_file else 'manual'
            )
            session.add(entry)
            session.flush()

            # Add players
            for i, name in enumerate(player_names):
                team = player_teams[i] if player_teams and i < len(player_teams) else None
                pos = player_positions[i] if player_positions and i < len(player_positions) else None

                player = self.get_or_create_player(name, team, pos)

                # Use raw SQL insert for association table with pick info
                session.execute(
                    draft_entry_players.insert().values(
                        draft_entry_id=entry.id,
                        player_id=player.id,
                        pick_number=i + 1,
                        round_number=i + 1
                    )
                )

            session.commit()
            session.refresh(entry)
            return entry
        finally:
            session.close()

    def get_draft_entry(self, entry_id: int) -> Optional[DraftEntry]:
        """Get a draft entry with all players loaded."""
        session = self.get_session()
        try:
            entry = session.query(DraftEntry).filter(DraftEntry.id == entry_id).first()
            if entry:
                # Force load players
                _ = entry.players
            return entry
        finally:
            session.close()

    def get_all_draft_entries(self, contest_id: int = None) -> List[DraftEntry]:
        """Get all draft entries, optionally filtered by contest."""
        session = self.get_session()
        try:
            query = session.query(DraftEntry)
            if contest_id:
                query = query.filter(DraftEntry.contest_id == contest_id)
            entries = query.all()
            # Force load players for each entry
            for entry in entries:
                _ = entry.players
            return entries
        finally:
            session.close()

    def get_entry_players(self, entry_id: int) -> List[Dict[str, Any]]:
        """Get players for an entry with pick information."""
        session = self.get_session()
        try:
            results = session.query(
                Player, draft_entry_players.c.pick_number, draft_entry_players.c.round_number
            ).join(
                draft_entry_players, Player.id == draft_entry_players.c.player_id
            ).filter(
                draft_entry_players.c.draft_entry_id == entry_id
            ).order_by(draft_entry_players.c.pick_number).all()

            return [
                {
                    'player': player,
                    'pick_number': pick,
                    'round_number': round_num,
                    'name': player.name,
                    'team': player.mlb_team,
                    'position': player.position
                }
                for player, pick, round_num in results
            ]
        finally:
            session.close()

    def delete_draft_entry(self, entry_id: int) -> bool:
        """Delete a draft entry."""
        session = self.get_session()
        try:
            entry = session.query(DraftEntry).filter(DraftEntry.id == entry_id).first()
            if entry:
                session.delete(entry)
                session.commit()
                return True
            return False
        finally:
            session.close()

    # ==================== Team Operations ====================

    def get_mlb_team(self, abbreviation: str) -> Optional[Team]:
        """Get MLB team by abbreviation."""
        session = self.get_session()
        try:
            return session.query(Team).filter(
                Team.abbreviation == abbreviation.upper()
            ).first()
        finally:
            session.close()

    def get_all_mlb_teams(self) -> List[Team]:
        """Get all MLB teams."""
        session = self.get_session()
        try:
            return session.query(Team).order_by(Team.division, Team.name).all()
        finally:
            session.close()

    # ==================== Statistics ====================

    def get_player_exposure(self, player_id: int = None, player_name: str = None) -> Dict[str, Any]:
        """Get exposure stats for a player across all entries."""
        session = self.get_session()
        try:
            total_entries = session.query(DraftEntry).count()
            if total_entries == 0:
                return {'exposure_rate': 0, 'entry_count': 0, 'total_entries': 0}

            if player_name:
                player = self.find_player(player_name)
                if player:
                    player_id = player.id

            if not player_id:
                return {'exposure_rate': 0, 'entry_count': 0, 'total_entries': 0}

            entry_count = session.query(draft_entry_players).filter(
                draft_entry_players.c.player_id == player_id
            ).count()

            return {
                'exposure_rate': entry_count / total_entries if total_entries > 0 else 0,
                'entry_count': entry_count,
                'total_entries': total_entries
            }
        finally:
            session.close()

    def get_database_stats(self) -> Dict[str, int]:
        """Get overall database statistics."""
        session = self.get_session()
        try:
            return {
                'total_players': session.query(Player).count(),
                'total_entries': session.query(DraftEntry).count(),
                'total_contests': session.query(Contest).count(),
                'total_teams': session.query(Team).count()
            }
        finally:
            session.close()

    # ==================== Utility Methods ====================

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize player name for matching."""
        if not name:
            return ""
        # Remove common suffixes, lowercase, strip whitespace
        normalized = name.lower().strip()
        for suffix in [' jr.', ' jr', ' sr.', ' sr', ' iii', ' ii', ' iv']:
            normalized = normalized.replace(suffix, '')
        # Remove periods and extra spaces
        normalized = normalized.replace('.', '').replace('  ', ' ')
        return normalized

    def close(self):
        """Close database connection."""
        self.engine.dispose()
