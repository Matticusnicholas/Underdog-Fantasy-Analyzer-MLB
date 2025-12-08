"""
Database models for the Fantasy Analyzer.
Stores players, teams, draft entries, and contests.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey,
    Table, Boolean, Text, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Association table for many-to-many relationship between DraftEntry and Player
draft_entry_players = Table(
    'draft_entry_players',
    Base.metadata,
    Column('draft_entry_id', Integer, ForeignKey('draft_entries.id'), primary_key=True),
    Column('player_id', Integer, ForeignKey('players.id'), primary_key=True),
    Column('pick_number', Integer),  # What pick number was this player taken
    Column('round_number', Integer),  # What round
)


class Player(Base):
    """MLB Player model."""
    __tablename__ = 'players'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    normalized_name = Column(String(100), nullable=False, index=True)  # For matching OCR results
    mlb_team = Column(String(50), index=True)  # MLB team abbreviation (NYY, LAD, etc.)
    position = Column(String(20))  # Primary position (P, C, 1B, 2B, SS, 3B, OF, DH)
    positions = Column(String(50))  # All eligible positions comma-separated

    # Stats and projections (optional, for future expansion)
    projected_points = Column(Float, default=0.0)
    adp = Column(Float)  # Average draft position

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    draft_entries = relationship(
        "DraftEntry",
        secondary=draft_entry_players,
        back_populates="players"
    )

    __table_args__ = (
        UniqueConstraint('normalized_name', 'mlb_team', name='unique_player_team'),
    )

    def __repr__(self):
        return f"<Player(name='{self.name}', team='{self.mlb_team}', pos='{self.position}')>"


class Contest(Base):
    """Contest/Tournament model for grouping draft entries."""
    __tablename__ = 'contests'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    platform = Column(String(50), default='Underdog')  # Underdog, DraftKings, etc.
    contest_type = Column(String(50), default='Best Ball')  # Best Ball, GPP, etc.
    entry_fee = Column(Float, default=0.0)
    max_entries = Column(Integer)
    start_date = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    draft_entries = relationship("DraftEntry", back_populates="contest")

    def __repr__(self):
        return f"<Contest(name='{self.name}', platform='{self.platform}')>"


class DraftEntry(Base):
    """A single draft entry (one team in a contest)."""
    __tablename__ = 'draft_entries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_name = Column(String(100))  # User-defined name for this entry
    contest_id = Column(Integer, ForeignKey('contests.id'))

    draft_position = Column(Integer)  # What pick slot (1-12, etc.)
    total_picks = Column(Integer, default=18)  # Standard MLB best ball is 18 rounds

    # Source tracking
    source_type = Column(String(50), default='screenshot')  # screenshot, manual, api
    source_file = Column(String(500))  # Path to screenshot if applicable

    # Notes
    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contest = relationship("Contest", back_populates="draft_entries")
    players = relationship(
        "Player",
        secondary=draft_entry_players,
        back_populates="draft_entries"
    )

    def __repr__(self):
        return f"<DraftEntry(id={self.id}, name='{self.entry_name}', players={len(self.players)})>"


class Team(Base):
    """
    MLB Team reference data.
    Used for stack analysis and team correlation.
    """
    __tablename__ = 'mlb_teams'

    id = Column(Integer, primary_key=True, autoincrement=True)
    abbreviation = Column(String(10), unique=True, nullable=False)  # NYY, LAD, etc.
    name = Column(String(100), nullable=False)  # New York Yankees
    city = Column(String(100))  # New York
    division = Column(String(20))  # AL East, NL West, etc.
    league = Column(String(5))  # AL or NL

    # Park factors (for advanced analysis)
    park_factor = Column(Float, default=1.0)

    def __repr__(self):
        return f"<Team(abbr='{self.abbreviation}', name='{self.name}')>"


class StackGroup(Base):
    """
    Tracks identified stacks (groups of players from same team) in entries.
    Pre-computed for faster analysis.
    """
    __tablename__ = 'stack_groups'

    id = Column(Integer, primary_key=True, autoincrement=True)
    draft_entry_id = Column(Integer, ForeignKey('draft_entries.id'))
    mlb_team = Column(String(10))  # Team abbreviation
    stack_size = Column(Integer)  # Number of players in this stack
    player_ids = Column(String(200))  # Comma-separated player IDs
    player_names = Column(Text)  # Comma-separated player names for quick display

    includes_pitcher = Column(Boolean, default=False)
    hitter_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<StackGroup(team='{self.mlb_team}', size={self.stack_size})>"


class PlayerCorrelation(Base):
    """
    Tracks how often player pairs appear together across entries.
    Pre-computed for correlation analysis.
    """
    __tablename__ = 'player_correlations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    player1_id = Column(Integer, ForeignKey('players.id'))
    player2_id = Column(Integer, ForeignKey('players.id'))

    times_paired = Column(Integer, default=0)  # Number of entries with both players
    total_entries_checked = Column(Integer, default=0)
    correlation_rate = Column(Float, default=0.0)  # times_paired / total_entries

    # Context
    same_team = Column(Boolean, default=False)  # Are they on the same MLB team?

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('player1_id', 'player2_id', name='unique_player_pair'),
    )

    def __repr__(self):
        return f"<PlayerCorrelation(p1={self.player1_id}, p2={self.player2_id}, rate={self.correlation_rate:.2%})>"
