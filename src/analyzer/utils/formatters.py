"""
Output formatting utilities for CLI and reports.
"""

from typing import List, Dict, Any, Optional
from tabulate import tabulate


def format_percentage(value: float, decimal_places: int = 1) -> str:
    """Format a decimal as percentage string."""
    return f"{value * 100:.{decimal_places}f}%"


def format_table(data: List[Dict[str, Any]],
                 columns: List[str] = None,
                 headers: List[str] = None,
                 tablefmt: str = "simple") -> str:
    """
    Format data as a text table.

    Args:
        data: List of dictionaries with data
        columns: Which columns to include (defaults to all keys)
        headers: Header names (defaults to column keys)
        tablefmt: Table format (simple, grid, pipe, etc.)

    Returns:
        Formatted table string
    """
    if not data:
        return "No data to display"

    if columns is None:
        columns = list(data[0].keys())

    if headers is None:
        headers = columns

    rows = [[row.get(col, '') for col in columns] for row in data]

    return tabulate(rows, headers=headers, tablefmt=tablefmt)


def format_player_list(players: List[Dict[str, Any]], numbered: bool = True) -> str:
    """Format a list of players for display."""
    lines = []
    for i, player in enumerate(players, 1):
        name = player.get('name', 'Unknown')
        team = player.get('team', '')
        pos = player.get('position', '')

        line = f"{name}"
        if pos or team:
            details = []
            if pos:
                details.append(pos)
            if team:
                details.append(team)
            line += f" ({', '.join(details)})"

        if numbered:
            line = f"{i:2d}. {line}"

        lines.append(line)

    return '\n'.join(lines)


def format_exposure_report(exposure_data: Dict[str, Any]) -> str:
    """Format exposure data as a readable report."""
    lines = []

    # Summary section
    summary = exposure_data.get('summary', {})
    lines.append("=" * 50)
    lines.append("EXPOSURE SUMMARY")
    lines.append("=" * 50)
    lines.append(f"Total Entries: {summary.get('total_entries', 0)}")
    lines.append(f"Unique Players: {summary.get('unique_players', 0)}")
    lines.append(f"Unique Teams: {summary.get('unique_teams', 0)}")
    lines.append("")

    # Top exposed players
    lines.append("TOP 10 EXPOSED PLAYERS:")
    lines.append("-" * 40)
    for player in exposure_data.get('player_exposure', [])[:10]:
        lines.append(
            f"  {player.name:<25} {player.team or '':>5} "
            f"{format_percentage(player.exposure_rate):>7} "
            f"({player.entry_count}/{player.total_entries})"
        )

    lines.append("")

    # Team exposure
    lines.append("TEAM EXPOSURE:")
    lines.append("-" * 40)
    for team in exposure_data.get('team_exposure', [])[:10]:
        lines.append(
            f"  {team.team:<5} {team.total_players_owned:>3} players "
            f"({team.unique_players} unique)"
        )

    return '\n'.join(lines)


def format_stack_report(stack_data: Dict[str, Any]) -> str:
    """Format stack analysis as a readable report."""
    lines = []

    summary = stack_data.get('summary', {})
    lines.append("=" * 50)
    lines.append("STACK ANALYSIS")
    lines.append("=" * 50)
    lines.append(f"Total Entries: {summary.get('total_entries', 0)}")
    lines.append(f"Total Stacks Found: {summary.get('total_stacks', 0)}")
    lines.append(f"Entries with Stacks: {summary.get('entries_with_stacks', 0)}")
    lines.append(f"Stack Coverage: {format_percentage(summary.get('stack_coverage', 0))}")
    lines.append("")

    # Stacks by size
    lines.append("STACKS BY SIZE:")
    for size, count in sorted(summary.get('stacks_by_size', {}).items()):
        lines.append(f"  {size}-Player Stacks: {count}")
    lines.append("")

    # Team summaries
    lines.append("TOP STACKED TEAMS:")
    lines.append("-" * 40)
    for team_sum in stack_data.get('team_summaries', [])[:10]:
        lines.append(
            f"  {team_sum.mlb_team:<5} {team_sum.total_stacks:>3} stacks "
            f"(avg {team_sum.avg_stack_size:.1f}, max {team_sum.max_stack_size})"
        )

    lines.append("")

    # Top combos
    lines.append("MOST COMMON STACK COMBOS:")
    lines.append("-" * 40)
    for combo in stack_data.get('stack_combos', [])[:10]:
        players_str = ', '.join(combo.players[:3])
        if len(combo.players) > 3:
            players_str += f" +{len(combo.players)-3}"
        lines.append(
            f"  {combo.mlb_team} {combo.stack_size}-Stack: "
            f"{combo.occurrences}x ({format_percentage(combo.occurrence_rate)})"
        )
        lines.append(f"    {players_str}")

    return '\n'.join(lines)


def format_correlation_report(correlation_data: Dict[str, Any]) -> str:
    """Format correlation analysis as a readable report."""
    lines = []

    summary = correlation_data.get('summary', {})
    lines.append("=" * 50)
    lines.append("CORRELATION ANALYSIS")
    lines.append("=" * 50)
    lines.append(f"Total Entries: {summary.get('total_entries', 0)}")
    lines.append(f"Unique Pairs Found: {summary.get('total_unique_pairs', 0)}")
    lines.append(f"Same-Team Pairs: {summary.get('same_team_pairs', 0)}")
    lines.append(f"High Correlation (50%+): {summary.get('high_correlation_pairs', 0)}")
    lines.append("")

    # Top pairs
    lines.append("TOP 15 PLAYER PAIRINGS:")
    lines.append("-" * 50)
    for pair in correlation_data.get('pairs', [])[:15]:
        same_team = "*" if pair.same_mlb_team else " "
        lines.append(
            f"  {same_team} {pair.player1_name:<20} + {pair.player2_name:<20} "
            f"{format_percentage(pair.correlation_rate):>7} ({pair.times_paired}x)"
        )

    lines.append("")
    lines.append("  * = Same MLB Team")
    lines.append("")

    # Group analysis
    for n in [3, 4, 5]:
        groups = correlation_data.get('groups', {}).get(n, [])
        if groups:
            lines.append(f"TOP {n}-PLAYER COMBOS:")
            lines.append("-" * 40)
            for group in groups[:5]:
                lines.append(
                    f"  {group.occurrences}x: {' + '.join(group.players)}"
                )
            lines.append("")

    return '\n'.join(lines)
