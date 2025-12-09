"""
Flask web application for the Fantasy Analyzer.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

# Import analyzer modules
from ..database.manager import DatabaseManager
from ..analysis.correlations import CorrelationAnalyzer
from ..analysis.exposure import ExposureCalculator
from ..analysis.stacks import StackFinder

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
UPLOAD_FOLDER = DATA_DIR / 'screenshots'
DB_PATH = DATA_DIR / 'fantasy.db'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Create Flask app
app = Flask(__name__,
            template_folder=str(Path(__file__).parent / 'templates'),
            static_folder=str(Path(__file__).parent / 'static'))

app.secret_key = os.environ.get('SECRET_KEY', 'fantasy-analyzer-secret-key-change-me')
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Ensure directories exist
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_db() -> DatabaseManager:
    """Get database manager instance."""
    return DatabaseManager(str(DB_PATH))


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_analysis_data(contest_id: Optional[int] = None):
    """Get all analysis data for dashboard."""
    db = get_db()
    entries = db.get_all_draft_entries(contest_id)

    if not entries:
        return None

    # Convert entries to analysis format
    entry_data = []
    for entry in entries:
        players = db.get_entry_players(entry.id)
        entry_data.append({
            'id': entry.id,
            'name': entry.entry_name,
            'players': players
        })

    # Run all analyses
    exposure_calc = ExposureCalculator()
    exposure_result = exposure_calc.calculate_from_entries(entry_data)

    stack_finder = StackFinder()
    stack_result = stack_finder.analyze_stacks(entry_data)

    corr_analyzer = CorrelationAnalyzer()
    corr_result = corr_analyzer.analyze_from_entries(entry_data)

    return {
        'entries': entry_data,
        'exposure': exposure_result,
        'stacks': stack_result,
        'correlations': corr_result,
        'total_entries': len(entries)
    }


# ==================== Routes ====================

@app.route('/')
def index():
    """Dashboard home page."""
    db = get_db()
    stats = db.get_database_stats()
    contests = db.get_all_contests()

    # Get analysis data
    analysis = get_analysis_data()

    return render_template('index.html',
                           stats=stats,
                           contests=contests,
                           analysis=analysis)


@app.route('/entries')
def entries_list():
    """List all draft entries."""
    db = get_db()
    contest_id = request.args.get('contest', type=int)
    entries = db.get_all_draft_entries(contest_id)
    contests = db.get_all_contests()

    return render_template('entries.html',
                           entries=entries,
                           contests=contests,
                           selected_contest=contest_id)


@app.route('/entry/<int:entry_id>')
def entry_detail(entry_id: int):
    """Show entry details."""
    db = get_db()
    entry = db.get_draft_entry(entry_id)

    if not entry:
        flash('Entry not found', 'error')
        return redirect(url_for('entries_list'))

    players = db.get_entry_players(entry_id)

    # Get stacks for this entry
    stack_finder = StackFinder()
    entry_data = {'id': entry_id, 'name': entry.entry_name, 'players': players}
    stacks = stack_finder.find_stacks_in_entry(entry_data)

    return render_template('entry_detail.html',
                           entry=entry,
                           players=players,
                           stacks=stacks)


@app.route('/entry/<int:entry_id>/delete', methods=['POST'])
def delete_entry(entry_id: int):
    """Delete an entry."""
    db = get_db()
    if db.delete_draft_entry(entry_id):
        flash('Entry deleted successfully', 'success')
    else:
        flash('Failed to delete entry', 'error')
    return redirect(url_for('entries_list'))


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload and parse screenshot."""
    if request.method == 'POST':
        # Check if file was uploaded
        if 'screenshot' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)

        file = request.files['screenshot']

        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Try to parse the screenshot
            try:
                from ..ocr.parser import DraftScreenshotParser
                parser = DraftScreenshotParser()
                platform = request.form.get('platform', 'auto')
                players = parser.parse_screenshot(filepath, platform)

                if players:
                    # Store in session for confirmation
                    return render_template('upload_confirm.html',
                                           players=players,
                                           filename=filename,
                                           entry_name=request.form.get('entry_name', ''),
                                           contest_id=request.form.get('contest_id'))
                else:
                    flash('No players found in image. Try manual entry.', 'warning')
                    return redirect(url_for('manual_entry'))

            except ImportError:
                flash('OCR not available. Please use manual entry.', 'warning')
                return redirect(url_for('manual_entry'))
            except Exception as e:
                flash(f'Error parsing image: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Invalid file type. Use PNG, JPG, or GIF.', 'error')
            return redirect(request.url)

    # GET request - show upload form
    db = get_db()
    contests = db.get_all_contests()
    return render_template('upload.html', contests=contests)


@app.route('/upload/confirm', methods=['POST'])
def upload_confirm():
    """Confirm and save parsed players."""
    db = get_db()

    # Get player data from form
    player_names = request.form.getlist('player_name')
    player_teams = request.form.getlist('player_team')
    player_positions = request.form.getlist('player_position')

    entry_name = request.form.get('entry_name') or f"Entry {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    contest_id = request.form.get('contest_id', type=int)
    filename = request.form.get('filename')

    # Filter out empty names
    valid_players = [(n, t, p) for n, t, p in zip(player_names, player_teams, player_positions) if n.strip()]

    if not valid_players:
        flash('No valid players to save', 'error')
        return redirect(url_for('upload'))

    names, teams, positions = zip(*valid_players)

    entry = db.create_draft_entry(
        player_names=list(names),
        player_teams=list(teams),
        player_positions=list(positions),
        contest_id=contest_id,
        entry_name=entry_name,
        source_file=filename
    )

    flash(f'Entry "{entry_name}" saved with {len(names)} players!', 'success')
    return redirect(url_for('entry_detail', entry_id=entry.id))


@app.route('/manual', methods=['GET', 'POST'])
def manual_entry():
    """Manual entry form."""
    if request.method == 'POST':
        db = get_db()

        entry_name = request.form.get('entry_name') or f"Entry {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        contest_id = request.form.get('contest_id', type=int)

        # Get player data
        player_names = request.form.getlist('player_name')
        player_teams = request.form.getlist('player_team')
        player_positions = request.form.getlist('player_position')

        # Filter out empty names
        valid_players = [(n, t, p) for n, t, p in zip(player_names, player_teams, player_positions) if n.strip()]

        if not valid_players:
            flash('Please enter at least one player', 'error')
            return redirect(request.url)

        names, teams, positions = zip(*valid_players)

        entry = db.create_draft_entry(
            player_names=list(names),
            player_teams=[t if t else None for t in teams],
            player_positions=[p if p else None for p in positions],
            contest_id=contest_id if contest_id else None,
            entry_name=entry_name
        )

        flash(f'Entry "{entry_name}" created with {len(names)} players!', 'success')
        return redirect(url_for('entry_detail', entry_id=entry.id))

    # GET request
    db = get_db()
    contests = db.get_all_contests()
    teams = db.get_all_mlb_teams()

    return render_template('manual_entry.html', contests=contests, teams=teams)


@app.route('/exposure')
def exposure():
    """Exposure analysis page."""
    db = get_db()
    contest_id = request.args.get('contest', type=int)
    contests = db.get_all_contests()

    analysis = get_analysis_data(contest_id)

    if not analysis:
        flash('No entries to analyze. Add some entries first!', 'info')
        return redirect(url_for('upload'))

    return render_template('exposure.html',
                           analysis=analysis,
                           contests=contests,
                           selected_contest=contest_id)


@app.route('/stacks')
def stacks():
    """Stack analysis page."""
    db = get_db()
    contest_id = request.args.get('contest', type=int)
    contests = db.get_all_contests()

    analysis = get_analysis_data(contest_id)

    if not analysis:
        flash('No entries to analyze. Add some entries first!', 'info')
        return redirect(url_for('upload'))

    return render_template('stacks.html',
                           analysis=analysis,
                           contests=contests,
                           selected_contest=contest_id)


@app.route('/correlations')
def correlations():
    """Correlation analysis page."""
    db = get_db()
    contest_id = request.args.get('contest', type=int)
    contests = db.get_all_contests()

    analysis = get_analysis_data(contest_id)

    if not analysis:
        flash('No entries to analyze. Add some entries first!', 'info')
        return redirect(url_for('upload'))

    return render_template('correlations.html',
                           analysis=analysis,
                           contests=contests,
                           selected_contest=contest_id)


@app.route('/contests')
def contests_list():
    """List and manage contests."""
    db = get_db()
    contests = db.get_all_contests()
    return render_template('contests.html', contests=contests)


@app.route('/contest/create', methods=['POST'])
def create_contest():
    """Create a new contest."""
    db = get_db()

    name = request.form.get('name')
    platform = request.form.get('platform', 'Underdog')
    contest_type = request.form.get('contest_type', 'Best Ball')
    entry_fee = request.form.get('entry_fee', 0, type=float)

    if not name:
        flash('Contest name is required', 'error')
        return redirect(url_for('contests_list'))

    contest = db.create_contest(name, platform, contest_type, entry_fee)
    flash(f'Contest "{name}" created!', 'success')
    return redirect(url_for('contests_list'))


# ==================== API Endpoints ====================

@app.route('/api/stats')
def api_stats():
    """Get database stats as JSON."""
    db = get_db()
    return jsonify(db.get_database_stats())


@app.route('/api/exposure')
def api_exposure():
    """Get exposure data as JSON."""
    contest_id = request.args.get('contest', type=int)
    analysis = get_analysis_data(contest_id)

    if not analysis:
        return jsonify({'error': 'No data available'}), 404

    exposure = analysis['exposure']

    return jsonify({
        'summary': exposure['summary'],
        'players': [
            {
                'name': p.name,
                'team': p.team,
                'position': p.position,
                'entries': p.entry_count,
                'total': p.total_entries,
                'rate': p.exposure_rate,
                'avg_pick': p.avg_pick
            }
            for p in exposure['player_exposure'][:50]
        ],
        'teams': [
            {
                'team': t.team,
                'total_players': t.total_players_owned,
                'unique_players': t.unique_players
            }
            for t in exposure['team_exposure']
        ]
    })


@app.route('/api/stacks')
def api_stacks():
    """Get stack data as JSON."""
    contest_id = request.args.get('contest', type=int)
    analysis = get_analysis_data(contest_id)

    if not analysis:
        return jsonify({'error': 'No data available'}), 404

    stacks = analysis['stacks']

    return jsonify({
        'summary': stacks['summary'],
        'teams': [
            {
                'team': t.mlb_team,
                'total_stacks': t.total_stacks,
                'avg_size': t.avg_stack_size,
                'max_size': t.max_stack_size,
                'stack_rate': t.stack_rate
            }
            for t in stacks['team_summaries'][:20]
        ]
    })


@app.route('/api/import', methods=['POST'])
def api_import():
    """Import entries from JSON."""
    if not request.is_json:
        return jsonify({'error': 'JSON required'}), 400

    data = request.get_json()
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
            entry_name=entry_data.get('name')
        )
        count += 1

    return jsonify({'imported': count})


@app.route('/api/export')
def api_export():
    """Export all entries as JSON."""
    db = get_db()
    contest_id = request.args.get('contest', type=int)
    entries = db.get_all_draft_entries(contest_id)

    data = []
    for entry in entries:
        players = db.get_entry_players(entry.id)
        data.append({
            'id': entry.id,
            'name': entry.entry_name,
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

    return jsonify(data)


# ==================== Template Filters ====================

@app.template_filter('percentage')
def percentage_filter(value):
    """Format as percentage."""
    if value is None:
        return '-'
    return f"{value * 100:.1f}%"


@app.template_filter('number')
def number_filter(value, decimals=1):
    """Format number with decimals."""
    if value is None:
        return '-'
    return f"{value:.{decimals}f}"


def run_app(host='0.0.0.0', port=5000, debug=True):
    """Run the Flask application."""
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_app()
