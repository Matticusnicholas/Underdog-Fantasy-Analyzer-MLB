"""
Correlation analysis for player pairings and lineup combinations.
Finds which players appear together across multiple draft entries.
"""

from typing import List, Dict, Any, Tuple, Optional
from itertools import combinations
from collections import defaultdict
from dataclasses import dataclass

import pandas as pd
import numpy as np


@dataclass
class PlayerPairing:
    """Represents a pairing of players across entries."""
    player1_name: str
    player2_name: str
    player1_team: Optional[str]
    player2_team: Optional[str]
    times_paired: int
    total_entries: int
    correlation_rate: float
    same_mlb_team: bool

    def __repr__(self):
        return f"{self.player1_name} + {self.player2_name}: {self.correlation_rate:.1%}"


@dataclass
class PlayerGroup:
    """Represents a group of N players appearing together."""
    players: List[str]
    player_teams: List[str]
    group_size: int
    occurrences: int
    total_entries: int
    occurrence_rate: float
    entry_ids: List[int]

    def __repr__(self):
        names = ", ".join(self.players[:3])
        if len(self.players) > 3:
            names += f" +{len(self.players)-3} more"
        return f"[{names}]: {self.occurrences}x ({self.occurrence_rate:.1%})"


class CorrelationAnalyzer:
    """
    Analyzes correlations between players across draft entries.

    Key features:
    - Find player pairs that appear together frequently
    - Identify N-player combinations (2, 3, 4, 5+)
    - Calculate correlation rates
    - Identify same-team stacks
    """

    def __init__(self, db_manager=None):
        """
        Initialize the analyzer.

        Args:
            db_manager: Optional DatabaseManager instance
        """
        self.db = db_manager

    def analyze_from_entries(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze correlations from a list of entry dictionaries.

        Args:
            entries: List of entries, each with 'players' list containing
                     player dicts with 'name' and 'team' keys

        Returns:
            Analysis results dictionary
        """
        if not entries:
            return {'pairs': [], 'groups': {}, 'summary': {}}

        # Build player-to-entries mapping
        player_entries = defaultdict(set)  # player_name -> set of entry indices
        player_teams = {}  # player_name -> team

        for i, entry in enumerate(entries):
            for player in entry.get('players', []):
                name = player.get('name', '')
                if name:
                    player_entries[name].add(i)
                    if player.get('team'):
                        player_teams[name] = player['team']

        total_entries = len(entries)

        # Calculate pair correlations
        pairs = self._find_pairs(player_entries, player_teams, total_entries)

        # Find N-player groups
        groups = {}
        for n in [2, 3, 4, 5]:
            groups[n] = self._find_groups(entries, n, player_teams)

        # Summary statistics
        summary = self._calculate_summary(pairs, groups, total_entries)

        return {
            'pairs': pairs,
            'groups': groups,
            'summary': summary,
            'total_entries': total_entries
        }

    def _find_pairs(self, player_entries: Dict[str, set],
                    player_teams: Dict[str, str],
                    total_entries: int,
                    min_occurrences: int = 2) -> List[PlayerPairing]:
        """Find all player pairs that appear together."""
        pairs = []
        players = list(player_entries.keys())

        for p1, p2 in combinations(players, 2):
            shared_entries = player_entries[p1] & player_entries[p2]
            times_paired = len(shared_entries)

            if times_paired >= min_occurrences:
                team1 = player_teams.get(p1)
                team2 = player_teams.get(p2)

                pairs.append(PlayerPairing(
                    player1_name=p1,
                    player2_name=p2,
                    player1_team=team1,
                    player2_team=team2,
                    times_paired=times_paired,
                    total_entries=total_entries,
                    correlation_rate=times_paired / total_entries,
                    same_mlb_team=(team1 == team2 and team1 is not None)
                ))

        # Sort by correlation rate descending
        pairs.sort(key=lambda x: x.correlation_rate, reverse=True)

        return pairs

    def _find_groups(self, entries: List[Dict[str, Any]], group_size: int,
                     player_teams: Dict[str, str],
                     min_occurrences: int = 2) -> List[PlayerGroup]:
        """Find all N-player groups that appear together."""
        group_counts = defaultdict(list)  # frozenset of names -> list of entry indices

        for i, entry in enumerate(entries):
            players = entry.get('players', [])
            names = [p['name'] for p in players if p.get('name')]

            if len(names) >= group_size:
                for combo in combinations(sorted(names), group_size):
                    group_counts[combo].append(i)

        total_entries = len(entries)
        groups = []

        for player_tuple, entry_indices in group_counts.items():
            if len(entry_indices) >= min_occurrences:
                player_list = list(player_tuple)
                teams = [player_teams.get(p) for p in player_list]

                groups.append(PlayerGroup(
                    players=player_list,
                    player_teams=teams,
                    group_size=group_size,
                    occurrences=len(entry_indices),
                    total_entries=total_entries,
                    occurrence_rate=len(entry_indices) / total_entries,
                    entry_ids=entry_indices
                ))

        # Sort by occurrences descending
        groups.sort(key=lambda x: x.occurrences, reverse=True)

        return groups

    def _calculate_summary(self, pairs: List[PlayerPairing],
                           groups: Dict[int, List[PlayerGroup]],
                           total_entries: int) -> Dict[str, Any]:
        """Calculate summary statistics."""
        same_team_pairs = [p for p in pairs if p.same_mlb_team]

        summary = {
            'total_unique_pairs': len(pairs),
            'same_team_pairs': len(same_team_pairs),
            'high_correlation_pairs': len([p for p in pairs if p.correlation_rate >= 0.5]),
            'total_entries': total_entries,
        }

        # Add group summaries
        for n, group_list in groups.items():
            summary[f'{n}_player_combos'] = len(group_list)
            summary[f'{n}_player_high_freq'] = len([g for g in group_list if g.occurrence_rate >= 0.3])

        return summary

    def get_player_connections(self, player_name: str,
                               entries: List[Dict[str, Any]],
                               min_shared: int = 2) -> List[Tuple[str, int, float]]:
        """
        Get all players that share entries with a specific player.

        Returns list of (other_player_name, shared_count, rate) tuples.
        """
        player_entries = defaultdict(set)

        for i, entry in enumerate(entries):
            for player in entry.get('players', []):
                name = player.get('name', '')
                if name:
                    player_entries[name].add(i)

        if player_name not in player_entries:
            return []

        target_entries = player_entries[player_name]
        connections = []

        for other_name, other_entries in player_entries.items():
            if other_name != player_name:
                shared = len(target_entries & other_entries)
                if shared >= min_shared:
                    rate = shared / len(target_entries)
                    connections.append((other_name, shared, rate))

        connections.sort(key=lambda x: x[1], reverse=True)
        return connections

    def find_unique_lineups(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find entries with unique player combinations.

        Returns entries that have combinations not found in other entries.
        """
        # Hash each lineup
        lineup_hashes = {}
        for i, entry in enumerate(entries):
            players = sorted([p['name'] for p in entry.get('players', []) if p.get('name')])
            lineup_hash = hash(tuple(players))

            if lineup_hash not in lineup_hashes:
                lineup_hashes[lineup_hash] = []
            lineup_hashes[lineup_hash].append(i)

        # Find unique ones
        unique_indices = [indices[0] for indices in lineup_hashes.values() if len(indices) == 1]

        return [entries[i] for i in unique_indices]

    def find_duplicate_lineups(self, entries: List[Dict[str, Any]]) -> Dict[str, List[int]]:
        """
        Find duplicate or near-duplicate lineups.

        Returns dict mapping lineup hash to list of entry indices.
        """
        lineup_hashes = defaultdict(list)

        for i, entry in enumerate(entries):
            players = sorted([p['name'] for p in entry.get('players', []) if p.get('name')])
            lineup_key = ','.join(players)
            lineup_hashes[lineup_key].append(i)

        # Return only duplicates
        return {k: v for k, v in lineup_hashes.items() if len(v) > 1}

    def to_dataframe(self, pairs: List[PlayerPairing]) -> pd.DataFrame:
        """Convert pair analysis to pandas DataFrame."""
        data = []
        for pair in pairs:
            data.append({
                'Player 1': pair.player1_name,
                'Player 2': pair.player2_name,
                'Team 1': pair.player1_team,
                'Team 2': pair.player2_team,
                'Times Paired': pair.times_paired,
                'Total Entries': pair.total_entries,
                'Correlation %': f"{pair.correlation_rate:.1%}",
                'Same Team': pair.same_mlb_team
            })

        return pd.DataFrame(data)

    def groups_to_dataframe(self, groups: List[PlayerGroup]) -> pd.DataFrame:
        """Convert group analysis to pandas DataFrame."""
        data = []
        for group in groups:
            data.append({
                'Players': ' + '.join(group.players),
                'Size': group.group_size,
                'Occurrences': group.occurrences,
                'Rate': f"{group.occurrence_rate:.1%}",
                'Teams': ', '.join(set(t for t in group.player_teams if t))
            })

        return pd.DataFrame(data)
