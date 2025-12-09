# Underdog Fantasy Analyzer - MLB

A comprehensive tool for analyzing MLB best ball fantasy drafts. Features screenshot OCR parsing, correlation analysis, exposure tracking, and stack finding.

## Features

- **Beautiful Web Interface**: Modern, responsive dashboard with charts and visualizations
- **Screenshot OCR Parser**: Parse draft screenshots from Underdog, DraftKings, and other platforms
- **Exposure Analysis**: Track player ownership percentage across your portfolio
- **Stack Finder**: Identify team stacks and analyze stacking patterns
- **Correlation Analysis**: Find player pairings and N-player combinations (2, 3, 4, 5+)
- **Database Storage**: SQLite database for storing and querying all your entries
- **Export/Import**: JSON and CSV export for external analysis
- **CLI & Web**: Use via command line or web browser

## Installation

### Prerequisites

1. Python 3.9 or higher
2. Tesseract OCR (for screenshot parsing)

#### Installing Tesseract

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

### Install the Package

```bash
# Clone the repository
git clone https://github.com/yourusername/Underdog-Fantasy-Analyzer-MLB.git
cd Underdog-Fantasy-Analyzer-MLB

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Quick Start

### Option 1: Web Interface (Recommended)

The easiest way to use the analyzer is through the web interface:

```bash
# Start the web server
python run_web.py

# Open in browser
# http://localhost:5000
```

The web interface provides:
- **Dashboard**: Overview of your portfolio with charts
- **Upload**: Drag & drop screenshot parsing
- **Manual Entry**: Add entries with auto-complete
- **Exposure**: Visual exposure analysis with filters
- **Stacks**: Team stack breakdown and combos
- **Correlations**: Player pairing analysis

### Option 2: Command Line

### 1. Parse a Draft Screenshot

```bash
# Parse and save to database
fantasy-analyzer parse screenshot.png --save --name "Entry 1"

# Parse with platform hint
fantasy-analyzer parse screenshot.png -p underdog --save
```

### 2. Manual Entry via Text

```bash
# Enter players via copy/paste
fantasy-analyzer parse-text --save --name "Entry 2"
# Then paste your player list and press Ctrl+D
```

### 3. Add Entries Manually

```bash
fantasy-analyzer add --name "My Entry"
# Enter players one per line: Name, Team, Position
```

### 4. View Your Entries

```bash
# List all entries
fantasy-analyzer entries

# Show specific entry
fantasy-analyzer show 1
```

### 5. Analyze Exposure

```bash
# Full exposure report
fantasy-analyzer exposure

# Export to CSV
fantasy-analyzer exposure --export exposure.csv

# Top 10 only
fantasy-analyzer exposure --top 10
```

### 6. Analyze Stacks

```bash
# Full stack analysis
fantasy-analyzer stacks

# Filter by team
fantasy-analyzer stacks --team LAD

# Minimum 3-player stacks
fantasy-analyzer stacks --min-size 3
```

### 7. Analyze Correlations

```bash
# All correlations
fantasy-analyzer correlations

# Same-team pairs only
fantasy-analyzer correlations --same-team

# 3-player combos
fantasy-analyzer correlations --group-size 3
```

## Command Reference

### Screenshot Parsing

| Command | Description |
|---------|-------------|
| `parse <image>` | Parse a screenshot |
| `parse-text` | Parse from text input |
| `add` | Manually add entry |

**Options for `parse`:**
- `-p, --platform`: Platform type (auto, underdog, draftkings, generic)
- `-s, --save`: Save to database
- `-c, --contest`: Contest ID
- `-n, --name`: Entry name

### Analysis

| Command | Description |
|---------|-------------|
| `exposure` | Analyze player exposure |
| `stacks` | Analyze team stacks |
| `correlations` | Find player correlations |

**Common Options:**
- `-c, --contest`: Filter by contest
- `-t, --top`: Number of results to show
- `-e, --export`: Export to file

### Data Management

| Command | Description |
|---------|-------------|
| `entries` | List all entries |
| `show <id>` | Show entry details |
| `delete-entry <id>` | Delete an entry |
| `contests` | List contests |
| `create-contest` | Create new contest |
| `stats` | Database statistics |
| `export` | Export to JSON/CSV |
| `import` | Import from JSON |

## Understanding the Analysis

### Exposure Analysis

Exposure shows what percentage of your entries contain each player:
- **High exposure (50%+)**: You're heavily invested in this player
- **Low exposure (<10%)**: Limited exposure, could be a contrarian play
- **Optimal range (15-30%)**: Balanced exposure for most players

### Stack Analysis

MLB best ball rewards team stacks because:
- Players from the same team correlate positively
- Big offensive days come from multiple hitters performing well
- 3-4 player stacks from high-powered offenses are optimal

**Stack metrics:**
- **Stack Size**: Number of players from same team (2-6+)
- **Stack Rate**: % of entries with that team stacked
- **Common Combos**: Specific player combinations used repeatedly

### Correlation Analysis

Shows which players you're pairing together:
- **Same-team pairs**: Building correlated stacks
- **Cross-team pairs**: Players you're drafting regardless of stack
- **High correlation (50%+)**: These players are core to your builds

## Tips for Best Ball

1. **Target 3-4 player stacks** from elite offenses (LAD, ATL, HOU, etc.)
2. **Diversify pitcher exposure** to avoid single-game variance
3. **Check for duplicate lineups** using correlation analysis
4. **Balance exposure** - don't go above 60% on any single player
5. **Stack multiple games** per lineup for ceiling potential

## File Structure

```
Underdog-Fantasy-Analyzer-MLB/
├── src/analyzer/
│   ├── ocr/           # Screenshot parsing
│   ├── database/      # Data storage
│   ├── analysis/      # Analytics engine
│   ├── utils/         # Helpers
│   ├── web/           # Web application
│   │   ├── templates/ # HTML templates
│   │   ├── static/    # CSS, JS, images
│   │   └── app.py     # Flask routes
│   └── cli.py         # Command line interface
├── data/
│   ├── screenshots/   # Your draft screenshots
│   ├── exports/       # Exported data
│   └── fantasy.db     # SQLite database
├── run_web.py         # Web app launcher
└── tests/             # Test suite
```

## Supported Platforms

- **Underdog Fantasy** (primary support)
- **DraftKings**
- **FanDuel**
- Generic player list format

## Contributing

Contributions welcome! Please open an issue or submit a PR.

## License

MIT License
