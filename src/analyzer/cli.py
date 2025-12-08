"""
Command-line interface for the Fantasy Analyzer.
"""

import os
import sys
import json
from typing import Optional, List
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .database.manager import DatabaseManager
from .analysis.correlations import CorrelationAnalyzer
from .analysis.exposure import ExposureCalculator
from .analysis.stacks import StackFinder
from .utils.formatters import (
    format_exposure_report, format_stack_report, format_correlation_report
)

# Initialize Rich console
console = Console()

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
DB_PATH = DATA_DIR / 'fantasy.db'


def get_db() -> DatabaseManager:
    """Get database manager instance."""
    return DatabaseManager(str(DB_PATH))


@click.group()
@click.version_option(version='1.0.0', prog_name='Fantasy Analyzer')
def main():
    """
    Underdog Fantasy Analyzer - MLB Best Ball

    A tool for analyzing fantasy baseball drafts with screenshot parsing,
    correlation analysis, exposure tracking, and stack finding.
    """
    pass


# ==================== Screenshot Parsing ====================

@main.command('parse')
@click.argument('image_path', type=click.Path(exists=True))
@click.option('--platform', '-p', default='auto',
              type=click.Choice(['auto', 'underdog', 'draftkings', 'generic']),
              help='Platform type for parsing')
@click.option('--save', '-s', is_flag=True, help='Save parsed entry to database')
@click.option('--contest', '-c', type=int, help='Contest ID to associate with')
@click.option('--name', '-n', help='Name for this entry')
def parse_screenshot(image_path: str, platform: str, save: bool,
                     contest: Optional[int], name: Optional[str]):
    """
    Parse a draft screenshot to extract player information.

    Example:
        fantasy-analyzer parse screenshot.png --save --name "Entry 1"
    """
    try:
        from .ocr.parser import DraftScreenshotParser
    except ImportError:
        console.print("[red]OCR dependencies not installed.[/red]")
        console.print("Run: pip install pytesseract pillow opencv-python")
        console.print("Also install Tesseract: https://github.com/tesseract-ocr/tesseract")
        sys.exit(1)

    console.print(f"[cyan]Parsing screenshot:[/cyan] {image_path}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing image...", total=None)

        parser = DraftScreenshotParser()
        players = parser.parse_screenshot(image_path, platform)

        progress.update(task, description="Done!")

    if not players:
        console.print("[yellow]No players found in image.[/yellow]")
        console.print("Try using --platform to specify the format, or use 'add-manual' command.")
        return

    # Display results
    table = Table(title="Parsed Players", show_header=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Player", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Position", style="yellow")
    table.add_column("Confidence", style="magenta")

    for i, player in enumerate(players, 1):
        conf = f"{player.confidence:.0%}" if player.confidence < 1.0 else "High"
        table.add_row(
            str(i),
            player.name,
            player.team or "-",
            player.position or "-",
            conf
        )

    console.print(table)
    console.print(f"\n[green]Found {len(players)} players[/green]")

    if save:
        db = get_db()
        entry = db.create_draft_entry(
            player_names=[p.name for p in players],
            player_teams=[p.team for p in players],
            player_positions=[p.position for p in players],
            contest_id=contest,
            entry_name=name,
            source_file=image_path
        )
        console.print(f"[green]Saved as Entry #{entry.id}[/green]")


@main.command('parse-text')
@click.option('--save', '-s', is_flag=True, help='Save parsed entry to database')
@click.option('--contest', '-c', type=int, help='Contest ID')
@click.option('--name', '-n', help='Name for this entry')
def parse_text(save: bool, contest: Optional[int], name: Optional[str]):
    """
    Parse player list from text input (copy/paste).

    Enter players one per line, then press Ctrl+D (Unix) or Ctrl+Z (Windows).
    """
    console.print("[cyan]Paste your player list (one player per line):[/cyan]")
    console.print("[dim]Format: 'Player Name TEAM POS' or just 'Player Name'[/dim]")
    console.print("[dim]Press Ctrl+D (Unix) or Ctrl+Z (Windows) when done.[/dim]\n")

    try:
        lines = sys.stdin.read()
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        return

    try:
        from .ocr.parser import DraftScreenshotParser
        parser = DraftScreenshotParser()
        players = parser.parse_text(lines)
    except ImportError:
        # Fallback: simple line-by-line parsing
        players = []
        for line in lines.strip().split('\n'):
            if line.strip():
                from .ocr.parser import ParsedPlayer
                players.append(ParsedPlayer(name=line.strip()))

    if not players:
        console.print("[yellow]No players parsed.[/yellow]")
        return

    table = Table(title="Parsed Players")
    table.add_column("#", width=4)
    table.add_column("Player")
    table.add_column("Team")
    table.add_column("Position")

    for i, p in enumerate(players, 1):
        table.add_row(str(i), p.name, p.team or "-", p.position or "-")

    console.print(table)

    if save:
        db = get_db()
        entry = db.create_draft_entry(
            player_names=[p.name for p in players],
            player_teams=[p.team for p in players],
            player_positions=[p.position for p in players],
            contest_id=contest,
            entry_name=name
        )
        console.print(f"[green]Saved as Entry #{entry.id}[/green]")


# ==================== Manual Entry ====================

@main.command('add')
@click.option('--name', '-n', prompt='Entry name', help='Name for this entry')
@click.option('--contest', '-c', type=int, help='Contest ID')
def add_entry(name: str, contest: Optional[int]):
    """
    Manually add a new draft entry.

    Enter players one per line in format: Player Name, Team, Position
    """
    console.print(f"[cyan]Adding entry: {name}[/cyan]")
    console.print("[dim]Enter players one per line (format: Name, Team, Position)[/dim]")
    console.print("[dim]Press Enter twice when done.[/dim]\n")

    players = []
    teams = []
    positions = []

    while True:
        try:
            line = input(f"Player {len(players)+1}: ").strip()
        except EOFError:
            break

        if not line:
            if players:
                break
            continue

        parts = [p.strip() for p in line.split(',')]
        players.append(parts[0])
        teams.append(parts[1] if len(parts) > 1 else None)
        positions.append(parts[2] if len(parts) > 2 else None)

    if not players:
        console.print("[yellow]No players entered.[/yellow]")
        return

    db = get_db()
    entry = db.create_draft_entry(
        player_names=players,
        player_teams=teams,
        player_positions=positions,
        contest_id=contest,
        entry_name=name
    )

    console.print(f"\n[green]Created Entry #{entry.id} with {len(players)} players[/green]")


# ==================== Viewing Data ====================

@main.command('entries')
@click.option('--contest', '-c', type=int, help='Filter by contest ID')
@click.option('--limit', '-l', default=20, help='Number of entries to show')
def list_entries(contest: Optional[int], limit: int):
    """List all draft entries."""
    db = get_db()
    entries = db.get_all_draft_entries(contest)

    if not entries:
        console.print("[yellow]No entries found.[/yellow]")
        console.print("Use 'parse' or 'add' to create entries.")
        return

    table = Table(title=f"Draft Entries ({len(entries)} total)")
    table.add_column("ID", style="dim", width=5)
    table.add_column("Name", style="cyan")
    table.add_column("Players", style="green", justify="right")
    table.add_column("Contest", style="yellow")
    table.add_column("Created", style="dim")

    for entry in entries[:limit]:
        table.add_row(
            str(entry.id),
            entry.entry_name or f"Entry {entry.id}",
            str(len(entry.players)),
            str(entry.contest_id) if entry.contest_id else "-",
            entry.created_at.strftime("%Y-%m-%d") if entry.created_at else "-"
        )

    console.print(table)


@main.command('show')
@click.argument('entry_id', type=int)
def show_entry(entry_id: int):
    """Show details of a specific entry."""
    db = get_db()
    players = db.get_entry_players(entry_id)

    if not players:
        console.print(f"[red]Entry #{entry_id} not found or has no players.[/red]")
        return

    entry = db.get_draft_entry(entry_id)
    console.print(Panel(f"Entry: {entry.entry_name or entry_id}", style="cyan"))

    table = Table(show_header=True)
    table.add_column("Pick", width=5)
    table.add_column("Player", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Position", style="yellow")

    for p in players:
        table.add_row(
            str(p['pick_number']),
            p['name'],
            p['team'] or "-",
            p['position'] or "-"
        )

    console.print(table)


# ==================== Analysis Commands ====================

@main.command('exposure')
@click.option('--contest', '-c', type=int, help='Filter by contest')
@click.option('--top', '-t', default=20, help='Show top N players')
@click.option('--min-rate', '-m', type=float, help='Minimum exposure rate to show')
@click.option('--export', '-e', type=click.Path(), help='Export to CSV')
def analyze_exposure(contest: Optional[int], top: int, min_rate: Optional[float],
                     export: Optional[str]):
    """
    Analyze player exposure across all entries.

    Shows how much of each player you own across your portfolio.
    """
    db = get_db()
    entries = db.get_all_draft_entries(contest)

    if not entries:
        console.print("[yellow]No entries found.[/yellow]")
        return

    # Convert to analysis format
    entry_data = []
    for entry in entries:
        players = db.get_entry_players(entry.id)
        entry_data.append({
            'id': entry.id,
            'name': entry.entry_name,
            'players': players
        })

    calculator = ExposureCalculator()
    result = calculator.calculate_from_entries(entry_data)

    # Filter by min rate if specified
    player_exposure = result['player_exposure']
    if min_rate:
        player_exposure = [p for p in player_exposure if p.exposure_rate >= min_rate]

    # Display summary
    summary = result['summary']
    console.print(Panel("Exposure Analysis", style="cyan"))
    console.print(f"Total Entries: [green]{summary.get('total_entries', 0)}[/green]")
    console.print(f"Unique Players: [green]{summary.get('unique_players', 0)}[/green]")
    console.print(f"Max Exposure: [yellow]{summary.get('most_exposed_player')}[/yellow] "
                  f"({summary.get('most_exposed_rate', 0):.1%})")
    console.print()

    # Player table
    table = Table(title=f"Player Exposure (Top {top})")
    table.add_column("Player", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Pos", style="yellow")
    table.add_column("Entries", justify="right")
    table.add_column("Exposure", justify="right", style="magenta")
    table.add_column("Avg Pick", justify="right")

    for p in player_exposure[:top]:
        table.add_row(
            p.name,
            p.team or "-",
            p.position or "-",
            str(p.entry_count),
            f"{p.exposure_rate:.1%}",
            f"{p.avg_pick:.1f}" if p.avg_pick else "-"
        )

    console.print(table)

    # Team exposure
    console.print()
    team_table = Table(title="Team Exposure")
    team_table.add_column("Team", style="green")
    team_table.add_column("Total Players", justify="right")
    team_table.add_column("Unique", justify="right")
    team_table.add_column("Avg/Entry", justify="right")

    for t in result['team_exposure'][:15]:
        team_table.add_row(
            t.team,
            str(t.total_players_owned),
            str(t.unique_players),
            f"{t.avg_players_per_entry:.1f}"
        )

    console.print(team_table)

    if export:
        df = calculator.to_dataframe(player_exposure)
        df.to_csv(export, index=False)
        console.print(f"\n[green]Exported to {export}[/green]")


@main.command('stacks')
@click.option('--contest', '-c', type=int, help='Filter by contest')
@click.option('--min-size', '-m', default=2, help='Minimum stack size')
@click.option('--team', '-t', help='Filter by MLB team')
@click.option('--export', '-e', type=click.Path(), help='Export to CSV')
def analyze_stacks(contest: Optional[int], min_size: int, team: Optional[str],
                   export: Optional[str]):
    """
    Analyze team stacks across all entries.

    Identifies which MLB teams you're stacking and how.
    """
    db = get_db()
    entries = db.get_all_draft_entries(contest)

    if not entries:
        console.print("[yellow]No entries found.[/yellow]")
        return

    # Convert to analysis format
    entry_data = []
    for entry in entries:
        players = db.get_entry_players(entry.id)
        entry_data.append({
            'id': entry.id,
            'name': entry.entry_name,
            'players': players
        })

    finder = StackFinder()
    result = finder.analyze_stacks(entry_data, min_stack_size=min_size)

    # Filter by team if specified
    if team:
        result['all_stacks'] = [s for s in result['all_stacks'] if s.mlb_team == team.upper()]
        result['team_summaries'] = [s for s in result['team_summaries'] if s.mlb_team == team.upper()]

    # Display summary
    summary = result['summary']
    console.print(Panel("Stack Analysis", style="cyan"))
    console.print(f"Total Entries: [green]{summary.get('total_entries', 0)}[/green]")
    console.print(f"Total Stacks: [green]{summary.get('total_stacks', 0)}[/green]")
    console.print(f"Stack Coverage: [yellow]{summary.get('stack_coverage', 0):.1%}[/yellow]")
    console.print()

    # Size distribution
    console.print("Stacks by Size:")
    for size, count in sorted(summary.get('stacks_by_size', {}).items()):
        console.print(f"  {size}-Player: [cyan]{count}[/cyan]")
    console.print()

    # Team summaries
    table = Table(title="Team Stack Summary")
    table.add_column("Team", style="green")
    table.add_column("Stacks", justify="right")
    table.add_column("Avg Size", justify="right")
    table.add_column("Max", justify="right")
    table.add_column("Rate", justify="right", style="magenta")

    for t in result['team_summaries'][:15]:
        table.add_row(
            t.mlb_team,
            str(t.total_stacks),
            f"{t.avg_stack_size:.1f}",
            str(t.max_stack_size),
            f"{t.stack_rate:.1%}"
        )

    console.print(table)

    # Common combos
    if result['stack_combos']:
        console.print()
        combo_table = Table(title="Most Common Stack Combos")
        combo_table.add_column("Team", style="green")
        combo_table.add_column("Players", style="cyan")
        combo_table.add_column("Count", justify="right")
        combo_table.add_column("Rate", justify="right", style="magenta")

        for combo in result['stack_combos'][:10]:
            combo_table.add_row(
                combo.mlb_team,
                ', '.join(combo.players[:4]) + ('...' if len(combo.players) > 4 else ''),
                str(combo.occurrences),
                f"{combo.occurrence_rate:.1%}"
            )

        console.print(combo_table)

    if export:
        df = finder.stacks_to_dataframe(result['all_stacks'])
        df.to_csv(export, index=False)
        console.print(f"\n[green]Exported to {export}[/green]")


@main.command('correlations')
@click.option('--contest', '-c', type=int, help='Filter by contest')
@click.option('--top', '-t', default=20, help='Show top N correlations')
@click.option('--min-rate', '-m', type=float, default=0.1, help='Minimum correlation rate')
@click.option('--same-team', is_flag=True, help='Only show same-team pairs')
@click.option('--group-size', '-g', type=int, help='Show N-player groups (2-5)')
def analyze_correlations(contest: Optional[int], top: int, min_rate: float,
                         same_team: bool, group_size: Optional[int]):
    """
    Analyze player correlations and combinations.

    Shows which players appear together most frequently.
    """
    db = get_db()
    entries = db.get_all_draft_entries(contest)

    if not entries:
        console.print("[yellow]No entries found.[/yellow]")
        return

    # Convert to analysis format
    entry_data = []
    for entry in entries:
        players = db.get_entry_players(entry.id)
        entry_data.append({
            'id': entry.id,
            'name': entry.entry_name,
            'players': players
        })

    analyzer = CorrelationAnalyzer()
    result = analyzer.analyze_from_entries(entry_data)

    # Filter pairs
    pairs = result['pairs']
    pairs = [p for p in pairs if p.correlation_rate >= min_rate]
    if same_team:
        pairs = [p for p in pairs if p.same_mlb_team]

    # Display summary
    summary = result['summary']
    console.print(Panel("Correlation Analysis", style="cyan"))
    console.print(f"Total Entries: [green]{summary.get('total_entries', 0)}[/green]")
    console.print(f"Unique Pairs: [green]{summary.get('total_unique_pairs', 0)}[/green]")
    console.print(f"Same-Team Pairs: [yellow]{summary.get('same_team_pairs', 0)}[/yellow]")
    console.print(f"High Correlation (50%+): [magenta]{summary.get('high_correlation_pairs', 0)}[/magenta]")
    console.print()

    # Pairs table
    table = Table(title=f"Top {top} Player Pairings")
    table.add_column("Player 1", style="cyan")
    table.add_column("Player 2", style="cyan")
    table.add_column("Same Team", style="yellow")
    table.add_column("Count", justify="right")
    table.add_column("Rate", justify="right", style="magenta")

    for p in pairs[:top]:
        table.add_row(
            f"{p.player1_name} ({p.player1_team or '?'})",
            f"{p.player2_name} ({p.player2_team or '?'})",
            "Yes" if p.same_mlb_team else "No",
            str(p.times_paired),
            f"{p.correlation_rate:.1%}"
        )

    console.print(table)

    # Show specific group size if requested
    if group_size and group_size in result['groups']:
        console.print()
        groups = result['groups'][group_size][:10]
        if groups:
            group_table = Table(title=f"{group_size}-Player Combinations")
            group_table.add_column("Players", style="cyan")
            group_table.add_column("Count", justify="right")
            group_table.add_column("Rate", justify="right", style="magenta")

            for g in groups:
                group_table.add_row(
                    ' + '.join(g.players),
                    str(g.occurrences),
                    f"{g.occurrence_rate:.1%}"
                )

            console.print(group_table)


# ==================== Contest Management ====================

@main.command('contests')
def list_contests():
    """List all contests."""
    db = get_db()
    contests = db.get_all_contests()

    if not contests:
        console.print("[yellow]No contests found.[/yellow]")
        console.print("Use 'create-contest' to create one.")
        return

    table = Table(title="Contests")
    table.add_column("ID", style="dim", width=5)
    table.add_column("Name", style="cyan")
    table.add_column("Platform", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("Entry Fee", justify="right")

    for c in contests:
        table.add_row(
            str(c.id),
            c.name,
            c.platform,
            c.contest_type,
            f"${c.entry_fee:.2f}" if c.entry_fee else "Free"
        )

    console.print(table)


@main.command('create-contest')
@click.option('--name', '-n', prompt='Contest name', help='Contest name')
@click.option('--platform', '-p', default='Underdog',
              type=click.Choice(['Underdog', 'DraftKings', 'FanDuel', 'Other']),
              help='Platform')
@click.option('--type', '-t', 'contest_type', default='Best Ball',
              help='Contest type')
@click.option('--fee', '-f', type=float, default=0, help='Entry fee')
def create_contest(name: str, platform: str, contest_type: str, fee: float):
    """Create a new contest."""
    db = get_db()
    contest = db.create_contest(name, platform, contest_type, fee)
    console.print(f"[green]Created Contest #{contest.id}: {name}[/green]")


# ==================== Utility Commands ====================

@main.command('stats')
def show_stats():
    """Show database statistics."""
    db = get_db()
    stats = db.get_database_stats()

    console.print(Panel("Database Statistics", style="cyan"))
    console.print(f"Total Entries: [green]{stats['total_entries']}[/green]")
    console.print(f"Total Players: [green]{stats['total_players']}[/green]")
    console.print(f"Total Contests: [green]{stats['total_contests']}[/green]")
    console.print(f"MLB Teams: [green]{stats['total_teams']}[/green]")
    console.print(f"\nDatabase: {DB_PATH}")


@main.command('delete-entry')
@click.argument('entry_id', type=int)
@click.confirmation_option(prompt='Are you sure you want to delete this entry?')
def delete_entry(entry_id: int):
    """Delete a draft entry."""
    db = get_db()
    if db.delete_draft_entry(entry_id):
        console.print(f"[green]Deleted Entry #{entry_id}[/green]")
    else:
        console.print(f"[red]Entry #{entry_id} not found[/red]")


@main.command('export')
@click.argument('output_path', type=click.Path())
@click.option('--format', '-f', 'fmt', default='json',
              type=click.Choice(['json', 'csv']), help='Export format')
@click.option('--contest', '-c', type=int, help='Filter by contest')
def export_data(output_path: str, fmt: str, contest: Optional[int]):
    """Export all entries to JSON or CSV."""
    db = get_db()
    entries = db.get_all_draft_entries(contest)

    if not entries:
        console.print("[yellow]No entries to export.[/yellow]")
        return

    data = []
    for entry in entries:
        players = db.get_entry_players(entry.id)
        data.append({
            'id': entry.id,
            'name': entry.entry_name,
            'contest_id': entry.contest_id,
            'created_at': entry.created_at.isoformat() if entry.created_at else None,
            'players': [
                {
                    'name': p['name'],
                    'team': p['team'],
                    'position': p['position'],
                    'pick': p['pick_number']
                }
                for p in players
            ]
        })

    if fmt == 'json':
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
    else:
        import csv
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Entry ID', 'Entry Name', 'Pick', 'Player', 'Team', 'Position'])
            for entry in data:
                for p in entry['players']:
                    writer.writerow([
                        entry['id'], entry['name'], p['pick'],
                        p['name'], p['team'], p['position']
                    ])

    console.print(f"[green]Exported {len(data)} entries to {output_path}[/green]")


@main.command('import')
@click.argument('input_path', type=click.Path(exists=True))
@click.option('--contest', '-c', type=int, help='Contest ID to associate entries with')
def import_data(input_path: str, contest: Optional[int]):
    """Import entries from JSON file."""
    with open(input_path) as f:
        data = json.load(f)

    db = get_db()
    count = 0

    for entry_data in data:
        players = entry_data.get('players', [])
        if not players:
            continue

        db.create_draft_entry(
            player_names=[p['name'] for p in players],
            player_teams=[p.get('team') for p in players],
            player_positions=[p.get('position') for p in players],
            contest_id=contest or entry_data.get('contest_id'),
            entry_name=entry_data.get('name')
        )
        count += 1

    console.print(f"[green]Imported {count} entries[/green]")


if __name__ == '__main__':
    main()
