"""
Stack finder for identifying team-based player groupings in lineups.
Essential for baseball best ball where team stacks correlate for big days.
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field

import pandas as pd
import numpy as np


@dataclass
class Stack:
    """Represents a team stack within a lineup."""
    mlb_team: str
    players: List[str]
    positions: List[str]
    stack_size: int
    has_pitcher: bool
    hitter_count: int
    entry_id: Optional[int] = None
    entry_name: Optional[str] = None

    def __repr__(self):
        return f"{self.mlb_team} {self.stack_size}-Stack: {', '.join(self.players)}"


@dataclass
class StackSummary:
    """Summary of stacking patterns across entries."""
    mlb_team: str
    total_stacks: int
    stack_sizes: Dict[int, int]  # size -> count
    avg_stack_size: float
    max_stack_size: int
    total_players: int
    entries_with_stack: int
    total_entries: int
    stack_rate: float  # % of entries with this team stacked


@dataclass
class StackCombo:
    """A specific stack combination found across entries."""
    mlb_team: str
    players: List[str]
    stack_size: int
    occurrences: int
    total_entries: int
    occurrence_rate: float
    entry_ids: List[int] = field(default_factory=list)


class StackFinder:
    """
    Finds and analyzes team stacks across draft entries.

    MLB best ball stacks are crucial because:
    - Hitters from the same team correlate (same game environment)
    - Big offensive days often come from multiple hitters on same team
    - Pitcher + opposing hitters is a bring-back strategy
    """

    # Standard MLB positions
    PITCHER_POSITIONS = {'P', 'SP', 'RP'}
    HITTER_POSITIONS = {'C', '1B', '2B', 'SS', '3B', 'OF', 'LF', 'CF', 'RF', 'DH', 'UTIL'}

    def __init__(self, db_manager=None):
        """Initialize stack finder."""
        self.db = db_manager

    def find_stacks_in_entry(self, entry: Dict[str, Any],
                             min_stack_size: int = 2) -> List[Stack]:
        """
        Find all stacks in a single entry.

        Args:
            entry: Entry dict with 'players' list
            min_stack_size: Minimum players from same team to count as stack

        Returns:
            List of Stack objects found
        """
        # Group players by team
        team_players = defaultdict(list)

        for player in entry.get('players', []):
            team = player.get('team')
            if team:
                team_players[team].append({
                    'name': player.get('name', ''),
                    'position': player.get('position', '')
                })

        stacks = []
        entry_id = entry.get('id')
        entry_name = entry.get('entry_name', entry.get('name'))

        for team, players in team_players.items():
            if len(players) >= min_stack_size:
                positions = [p['position'] for p in players]
                has_pitcher = any(pos in self.PITCHER_POSITIONS for pos in positions)
                hitter_count = sum(1 for pos in positions if pos in self.HITTER_POSITIONS or not pos)

                stacks.append(Stack(
                    mlb_team=team,
                    players=[p['name'] for p in players],
                    positions=positions,
                    stack_size=len(players),
                    has_pitcher=has_pitcher,
                    hitter_count=hitter_count,
                    entry_id=entry_id,
                    entry_name=entry_name
                ))

        return stacks

    def analyze_stacks(self, entries: List[Dict[str, Any]],
                       min_stack_size: int = 2) -> Dict[str, Any]:
        """
        Comprehensive stack analysis across all entries.

        Args:
            entries: List of entry dictionaries
            min_stack_size: Minimum stack size to track

        Returns:
            Dict with all_stacks, team_summaries, stack_combos, summary
        """
        if not entries:
            return {
                'all_stacks': [],
                'team_summaries': [],
                'stack_combos': [],
                'summary': {}
            }

        total_entries = len(entries)
        all_stacks = []
        team_data = defaultdict(lambda: {
            'stacks': [],
            'sizes': defaultdict(int),
            'entries': set()
        })

        # Find stacks in each entry
        for i, entry in enumerate(entries):
            entry_stacks = self.find_stacks_in_entry(entry, min_stack_size)
            for stack in entry_stacks:
                stack.entry_id = i
                all_stacks.append(stack)

                team_data[stack.mlb_team]['stacks'].append(stack)
                team_data[stack.mlb_team]['sizes'][stack.stack_size] += 1
                team_data[stack.mlb_team]['entries'].add(i)

        # Build team summaries
        team_summaries = []
        for team, data in team_data.items():
            sizes = dict(data['sizes'])
            total_players = sum(s.stack_size for s in data['stacks'])

            team_summaries.append(StackSummary(
                mlb_team=team,
                total_stacks=len(data['stacks']),
                stack_sizes=sizes,
                avg_stack_size=total_players / len(data['stacks']) if data['stacks'] else 0,
                max_stack_size=max(sizes.keys()) if sizes else 0,
                total_players=total_players,
                entries_with_stack=len(data['entries']),
                total_entries=total_entries,
                stack_rate=len(data['entries']) / total_entries
            ))

        team_summaries.sort(key=lambda x: x.total_stacks, reverse=True)

        # Find common stack combinations
        stack_combos = self._find_stack_combos(all_stacks, total_entries)

        # Summary stats
        summary = self._calculate_summary(all_stacks, team_summaries, total_entries)

        return {
            'all_stacks': all_stacks,
            'team_summaries': team_summaries,
            'stack_combos': stack_combos,
            'summary': summary
        }

    def _find_stack_combos(self, all_stacks: List[Stack],
                           total_entries: int,
                           min_occurrences: int = 2) -> List[StackCombo]:
        """Find specific stack combinations that appear multiple times."""
        combo_counts = defaultdict(lambda: {'count': 0, 'entries': []})

        for stack in all_stacks:
            # Create a hashable key for this exact stack
            key = (stack.mlb_team, tuple(sorted(stack.players)))
            combo_counts[key]['count'] += 1
            combo_counts[key]['entries'].append(stack.entry_id)

        combos = []
        for (team, players), data in combo_counts.items():
            if data['count'] >= min_occurrences:
                combos.append(StackCombo(
                    mlb_team=team,
                    players=list(players),
                    stack_size=len(players),
                    occurrences=data['count'],
                    total_entries=total_entries,
                    occurrence_rate=data['count'] / total_entries,
                    entry_ids=data['entries']
                ))

        combos.sort(key=lambda x: x.occurrences, reverse=True)
        return combos

    def _calculate_summary(self, all_stacks: List[Stack],
                           team_summaries: List[StackSummary],
                           total_entries: int) -> Dict[str, Any]:
        """Calculate summary statistics."""
        if not all_stacks:
            return {
                'total_entries': total_entries,
                'total_stacks': 0
            }

        stack_sizes = [s.stack_size for s in all_stacks]
        entries_with_stacks = len(set(s.entry_id for s in all_stacks))

        # Count by size
        size_counts = defaultdict(int)
        for size in stack_sizes:
            size_counts[size] += 1

        summary = {
            'total_entries': total_entries,
            'total_stacks': len(all_stacks),
            'entries_with_stacks': entries_with_stacks,
            'stack_coverage': entries_with_stacks / total_entries if total_entries else 0,

            'avg_stack_size': np.mean(stack_sizes),
            'max_stack_size': max(stack_sizes),
            'min_stack_size': min(stack_sizes),

            'stacks_by_size': dict(size_counts),

            'unique_teams_stacked': len(team_summaries),
            'most_stacked_team': team_summaries[0].mlb_team if team_summaries else None,
            'most_stacked_count': team_summaries[0].total_stacks if team_summaries else 0,

            # Pitcher-inclusive stacks
            'stacks_with_pitcher': sum(1 for s in all_stacks if s.has_pitcher),
            'pure_hitter_stacks': sum(1 for s in all_stacks if not s.has_pitcher),
        }

        return summary

    def get_optimal_stacks(self, entries: List[Dict[str, Any]],
                           min_size: int = 3,
                           min_occurrences: int = 2) -> List[StackCombo]:
        """
        Get the most valuable stack combinations.

        Args:
            entries: Entry list
            min_size: Minimum stack size (3+ is usually valuable)
            min_occurrences: Minimum times the exact stack appears

        Returns:
            List of optimal stack combos
        """
        result = self.analyze_stacks(entries, min_stack_size=min_size)
        combos = [c for c in result['stack_combos'] if c.occurrences >= min_occurrences]
        return combos

    def get_team_stacking_strategy(self, entries: List[Dict[str, Any]],
                                   team: str) -> Dict[str, Any]:
        """
        Get detailed stacking analysis for a specific team.

        Returns breakdown of how you've stacked a particular team.
        """
        result = self.analyze_stacks(entries)

        team_stacks = [s for s in result['all_stacks'] if s.mlb_team == team]
        team_combos = [c for c in result['stack_combos'] if c.mlb_team == team]

        if not team_stacks:
            return {'team': team, 'stack_count': 0}

        # Player frequency in stacks
        player_freq = defaultdict(int)
        for stack in team_stacks:
            for player in stack.players:
                player_freq[player] += 1

        return {
            'team': team,
            'stack_count': len(team_stacks),
            'unique_combos': len(set(tuple(sorted(s.players)) for s in team_stacks)),
            'avg_size': np.mean([s.stack_size for s in team_stacks]),
            'max_size': max(s.stack_size for s in team_stacks),
            'size_distribution': {
                size: sum(1 for s in team_stacks if s.stack_size == size)
                for size in range(2, 7)
            },
            'player_frequency': dict(sorted(player_freq.items(),
                                            key=lambda x: x[1], reverse=True)),
            'top_combos': team_combos[:5],
            'with_pitcher': sum(1 for s in team_stacks if s.has_pitcher),
        }

    def find_game_stacks(self, entries: List[Dict[str, Any]],
                         team1: str, team2: str) -> Dict[str, Any]:
        """
        Find stacks from a specific game (both teams).
        Useful for identifying game-stack exposure.

        Args:
            entries: Entry list
            team1: First team (e.g., 'NYY')
            team2: Second team (e.g., 'BOS')

        Returns:
            Game stacking analysis
        """
        result = self.analyze_stacks(entries)

        game_stacks = [
            s for s in result['all_stacks']
            if s.mlb_team in (team1, team2)
        ]

        # Find entries with both teams
        entry_teams = defaultdict(set)
        for stack in game_stacks:
            entry_teams[stack.entry_id].add(stack.mlb_team)

        both_teams_entries = [
            eid for eid, teams in entry_teams.items()
            if team1 in teams and team2 in teams
        ]

        return {
            'game': f"{team1} vs {team2}",
            'total_stacks': len(game_stacks),
            f'{team1}_stacks': sum(1 for s in game_stacks if s.mlb_team == team1),
            f'{team2}_stacks': sum(1 for s in game_stacks if s.mlb_team == team2),
            'entries_with_game_stack': len(entry_teams),
            'entries_with_both_teams': len(both_teams_entries),
            'game_correlation_rate': len(entry_teams) / len(entries) if entries else 0,
        }

    def stacks_to_dataframe(self, stacks: List[Stack]) -> pd.DataFrame:
        """Convert stacks to DataFrame."""
        data = []
        for s in stacks:
            data.append({
                'Entry': s.entry_name or s.entry_id,
                'Team': s.mlb_team,
                'Size': s.stack_size,
                'Players': ', '.join(s.players),
                'Has Pitcher': 'Yes' if s.has_pitcher else 'No',
                'Hitters': s.hitter_count
            })
        return pd.DataFrame(data)

    def summaries_to_dataframe(self, summaries: List[StackSummary]) -> pd.DataFrame:
        """Convert team summaries to DataFrame."""
        data = []
        for s in summaries:
            sizes_str = ', '.join(f"{k}x{v}" for k, v in sorted(s.stack_sizes.items()))
            data.append({
                'Team': s.mlb_team,
                'Total Stacks': s.total_stacks,
                'Stack Sizes': sizes_str,
                'Avg Size': f"{s.avg_stack_size:.1f}",
                'Max Size': s.max_stack_size,
                'Entries': s.entries_with_stack,
                'Stack Rate': f"{s.stack_rate:.1%}"
            })
        return pd.DataFrame(data)
