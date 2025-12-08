"""
Exposure calculator for tracking player ownership across entries.
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from dataclasses import dataclass

import pandas as pd
import numpy as np


@dataclass
class PlayerExposure:
    """Exposure data for a single player."""
    name: str
    team: Optional[str]
    position: Optional[str]
    entry_count: int
    total_entries: int
    exposure_rate: float
    avg_pick: Optional[float] = None
    earliest_pick: Optional[int] = None
    latest_pick: Optional[int] = None
    entry_ids: List[int] = None

    def __repr__(self):
        return f"{self.name} ({self.team}): {self.exposure_rate:.1%} ({self.entry_count}/{self.total_entries})"


@dataclass
class TeamExposure:
    """Exposure data for an MLB team."""
    team: str
    total_players_owned: int
    unique_players: int
    total_entries: int
    avg_players_per_entry: float
    player_breakdown: Dict[str, int]  # player_name -> count


class ExposureCalculator:
    """
    Calculates exposure metrics for players and teams across draft entries.

    Key metrics:
    - Player exposure rate (% of entries containing player)
    - Average draft position (ADP) from your drafts
    - Team exposure (how much of each MLB team you own)
    - Position exposure (roster construction analysis)
    """

    def __init__(self, db_manager=None):
        """Initialize calculator."""
        self.db = db_manager

    def calculate_from_entries(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate all exposure metrics from a list of entries.

        Args:
            entries: List of entry dicts, each with 'players' list

        Returns:
            Dict with player_exposure, team_exposure, position_exposure, summary
        """
        if not entries:
            return {
                'player_exposure': [],
                'team_exposure': [],
                'position_exposure': {},
                'summary': {}
            }

        total_entries = len(entries)

        # Track player data
        player_data = defaultdict(lambda: {
            'count': 0,
            'picks': [],
            'team': None,
            'position': None,
            'entry_ids': []
        })

        # Track team data
        team_data = defaultdict(lambda: {
            'total_players': 0,
            'players': defaultdict(int),
            'entries_with_team': set()
        })

        # Track position data
        position_data = defaultdict(lambda: {'count': 0, 'players': set()})

        # Process all entries
        for entry_idx, entry in enumerate(entries):
            entry_teams = defaultdict(int)

            for player in entry.get('players', []):
                name = player.get('name', '')
                if not name:
                    continue

                team = player.get('team')
                position = player.get('position')
                pick = player.get('pick_number')

                # Player exposure
                player_data[name]['count'] += 1
                player_data[name]['entry_ids'].append(entry_idx)
                if pick:
                    player_data[name]['picks'].append(pick)
                if team:
                    player_data[name]['team'] = team
                if position:
                    player_data[name]['position'] = position

                # Team exposure
                if team:
                    team_data[team]['total_players'] += 1
                    team_data[team]['players'][name] += 1
                    entry_teams[team] += 1

                # Position exposure
                if position:
                    position_data[position]['count'] += 1
                    position_data[position]['players'].add(name)

            # Track entries with each team
            for team, count in entry_teams.items():
                team_data[team]['entries_with_team'].add(entry_idx)

        # Build player exposure list
        player_exposure = []
        for name, data in player_data.items():
            picks = data['picks']
            player_exposure.append(PlayerExposure(
                name=name,
                team=data['team'],
                position=data['position'],
                entry_count=data['count'],
                total_entries=total_entries,
                exposure_rate=data['count'] / total_entries,
                avg_pick=np.mean(picks) if picks else None,
                earliest_pick=min(picks) if picks else None,
                latest_pick=max(picks) if picks else None,
                entry_ids=data['entry_ids']
            ))

        # Sort by exposure rate descending
        player_exposure.sort(key=lambda x: x.exposure_rate, reverse=True)

        # Build team exposure list
        team_exposure = []
        for team, data in team_data.items():
            entries_count = len(data['entries_with_team'])
            team_exposure.append(TeamExposure(
                team=team,
                total_players_owned=data['total_players'],
                unique_players=len(data['players']),
                total_entries=total_entries,
                avg_players_per_entry=data['total_players'] / entries_count if entries_count else 0,
                player_breakdown=dict(data['players'])
            ))

        # Sort by total players owned
        team_exposure.sort(key=lambda x: x.total_players_owned, reverse=True)

        # Position exposure summary
        position_exposure = {
            pos: {
                'count': data['count'],
                'unique_players': len(data['players']),
                'avg_per_entry': data['count'] / total_entries
            }
            for pos, data in position_data.items()
        }

        # Summary statistics
        summary = self._calculate_summary(player_exposure, team_exposure,
                                          position_exposure, total_entries)

        return {
            'player_exposure': player_exposure,
            'team_exposure': team_exposure,
            'position_exposure': position_exposure,
            'summary': summary
        }

    def _calculate_summary(self, player_exposure: List[PlayerExposure],
                           team_exposure: List[TeamExposure],
                           position_exposure: Dict[str, Any],
                           total_entries: int) -> Dict[str, Any]:
        """Calculate summary statistics."""
        if not player_exposure:
            return {}

        exposure_rates = [p.exposure_rate for p in player_exposure]

        # Find high/low exposure players
        high_exposure = [p for p in player_exposure if p.exposure_rate >= 0.5]
        max_exposure = [p for p in player_exposure if p.exposure_rate >= 0.8]
        low_exposure = [p for p in player_exposure if p.exposure_rate <= 0.1]

        summary = {
            'total_entries': total_entries,
            'unique_players': len(player_exposure),
            'unique_teams': len(team_exposure),

            # Exposure distribution
            'avg_exposure': np.mean(exposure_rates),
            'median_exposure': np.median(exposure_rates),
            'max_exposure_rate': max(exposure_rates),
            'min_exposure_rate': min(exposure_rates),

            # Player categories
            'max_exposure_players': len(max_exposure),  # 80%+ exposure
            'high_exposure_players': len(high_exposure),  # 50%+ exposure
            'low_exposure_players': len(low_exposure),  # 10% or less

            # Top exposed player
            'most_exposed_player': player_exposure[0].name if player_exposure else None,
            'most_exposed_rate': player_exposure[0].exposure_rate if player_exposure else 0,

            # Team with most exposure
            'most_owned_team': team_exposure[0].team if team_exposure else None,
            'most_owned_team_players': team_exposure[0].total_players_owned if team_exposure else 0,
        }

        return summary

    def get_target_exposure(self, entries: List[Dict[str, Any]],
                            target_rate: float = 0.20) -> List[Dict[str, Any]]:
        """
        Find players near a target exposure rate.
        Useful for finding players to add or fade.

        Args:
            entries: List of entry dictionaries
            target_rate: Target exposure rate (default 20%)

        Returns:
            List of players near the target rate
        """
        result = self.calculate_from_entries(entries)
        player_exposure = result['player_exposure']

        # Find players within +/- 5% of target
        tolerance = 0.05
        targets = [
            p for p in player_exposure
            if abs(p.exposure_rate - target_rate) <= tolerance
        ]

        return [
            {
                'name': p.name,
                'team': p.team,
                'exposure': p.exposure_rate,
                'difference': p.exposure_rate - target_rate
            }
            for p in targets
        ]

    def get_overexposed_players(self, entries: List[Dict[str, Any]],
                                threshold: float = 0.40) -> List[PlayerExposure]:
        """Get players above exposure threshold."""
        result = self.calculate_from_entries(entries)
        return [p for p in result['player_exposure'] if p.exposure_rate >= threshold]

    def get_underexposed_players(self, entries: List[Dict[str, Any]],
                                 threshold: float = 0.10) -> List[PlayerExposure]:
        """Get players below exposure threshold."""
        result = self.calculate_from_entries(entries)
        return [p for p in result['player_exposure'] if p.exposure_rate <= threshold]

    def compare_to_field(self, entries: List[Dict[str, Any]],
                         field_exposure: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Compare your exposure to overall field exposure.

        Args:
            entries: Your entries
            field_exposure: Dict of player_name -> field_ownership_rate

        Returns:
            List of diffs showing over/under owned players
        """
        result = self.calculate_from_entries(entries)
        comparison = []

        for player in result['player_exposure']:
            field_rate = field_exposure.get(player.name, 0)
            diff = player.exposure_rate - field_rate

            comparison.append({
                'name': player.name,
                'team': player.team,
                'your_exposure': player.exposure_rate,
                'field_exposure': field_rate,
                'difference': diff,
                'leverage': 'OVER' if diff > 0.05 else 'UNDER' if diff < -0.05 else 'NEUTRAL'
            })

        # Sort by absolute difference
        comparison.sort(key=lambda x: abs(x['difference']), reverse=True)

        return comparison

    def to_dataframe(self, player_exposure: List[PlayerExposure]) -> pd.DataFrame:
        """Convert player exposure to DataFrame."""
        data = []
        for p in player_exposure:
            data.append({
                'Player': p.name,
                'Team': p.team,
                'Position': p.position,
                'Entries': p.entry_count,
                'Total': p.total_entries,
                'Exposure %': f"{p.exposure_rate:.1%}",
                'Avg Pick': f"{p.avg_pick:.1f}" if p.avg_pick else "-",
                'Pick Range': f"{p.earliest_pick}-{p.latest_pick}" if p.earliest_pick else "-"
            })

        return pd.DataFrame(data)

    def team_exposure_dataframe(self, team_exposure: List[TeamExposure]) -> pd.DataFrame:
        """Convert team exposure to DataFrame."""
        data = []
        for t in team_exposure:
            data.append({
                'Team': t.team,
                'Total Players': t.total_players_owned,
                'Unique Players': t.unique_players,
                'Avg Per Entry': f"{t.avg_players_per_entry:.1f}",
            })

        return pd.DataFrame(data)
