"""Tests for analysis modules."""

import pytest
from analyzer.analysis.correlations import CorrelationAnalyzer
from analyzer.analysis.exposure import ExposureCalculator
from analyzer.analysis.stacks import StackFinder


# Sample test data
SAMPLE_ENTRIES = [
    {
        'id': 1,
        'name': 'Entry 1',
        'players': [
            {'name': 'Shohei Ohtani', 'team': 'LAD', 'position': 'DH'},
            {'name': 'Mookie Betts', 'team': 'LAD', 'position': 'OF'},
            {'name': 'Aaron Judge', 'team': 'NYY', 'position': 'OF'},
            {'name': 'Juan Soto', 'team': 'NYY', 'position': 'OF'},
            {'name': 'Corey Seager', 'team': 'TEX', 'position': 'SS'},
        ]
    },
    {
        'id': 2,
        'name': 'Entry 2',
        'players': [
            {'name': 'Shohei Ohtani', 'team': 'LAD', 'position': 'DH'},
            {'name': 'Mookie Betts', 'team': 'LAD', 'position': 'OF'},
            {'name': 'Freddie Freeman', 'team': 'LAD', 'position': '1B'},
            {'name': 'Aaron Judge', 'team': 'NYY', 'position': 'OF'},
            {'name': 'Bobby Witt Jr', 'team': 'KC', 'position': 'SS'},
        ]
    },
    {
        'id': 3,
        'name': 'Entry 3',
        'players': [
            {'name': 'Ronald Acuna Jr', 'team': 'ATL', 'position': 'OF'},
            {'name': 'Matt Olson', 'team': 'ATL', 'position': '1B'},
            {'name': 'Aaron Judge', 'team': 'NYY', 'position': 'OF'},
            {'name': 'Juan Soto', 'team': 'NYY', 'position': 'OF'},
            {'name': 'Corey Seager', 'team': 'TEX', 'position': 'SS'},
        ]
    },
]


class TestCorrelationAnalyzer:
    """Tests for CorrelationAnalyzer."""

    def test_analyze_from_entries(self):
        """Test basic correlation analysis."""
        analyzer = CorrelationAnalyzer()
        result = analyzer.analyze_from_entries(SAMPLE_ENTRIES)

        assert 'pairs' in result
        assert 'groups' in result
        assert 'summary' in result
        assert result['total_entries'] == 3

    def test_find_pairs(self):
        """Test pair finding."""
        analyzer = CorrelationAnalyzer()
        result = analyzer.analyze_from_entries(SAMPLE_ENTRIES)

        # Aaron Judge appears in all 3 entries
        judge_pairs = [p for p in result['pairs'] if 'Aaron Judge' in (p.player1_name, p.player2_name)]
        assert len(judge_pairs) > 0

    def test_same_team_pairs(self):
        """Test same-team pair detection."""
        analyzer = CorrelationAnalyzer()
        result = analyzer.analyze_from_entries(SAMPLE_ENTRIES)

        # Ohtani + Betts are LAD teammates
        same_team = [p for p in result['pairs'] if p.same_mlb_team]
        assert len(same_team) > 0

    def test_group_finding(self):
        """Test N-player group finding."""
        analyzer = CorrelationAnalyzer()
        result = analyzer.analyze_from_entries(SAMPLE_ENTRIES)

        # Should have 2-player groups
        assert 2 in result['groups']
        assert len(result['groups'][2]) > 0

    def test_empty_entries(self):
        """Test with empty input."""
        analyzer = CorrelationAnalyzer()
        result = analyzer.analyze_from_entries([])

        assert result['pairs'] == []
        assert result['total_entries'] == 0


class TestExposureCalculator:
    """Tests for ExposureCalculator."""

    def test_calculate_exposure(self):
        """Test basic exposure calculation."""
        calculator = ExposureCalculator()
        result = calculator.calculate_from_entries(SAMPLE_ENTRIES)

        assert 'player_exposure' in result
        assert 'team_exposure' in result
        assert 'summary' in result

    def test_player_exposure_rate(self):
        """Test exposure rate calculation."""
        calculator = ExposureCalculator()
        result = calculator.calculate_from_entries(SAMPLE_ENTRIES)

        # Aaron Judge is in all 3 entries
        judge = next((p for p in result['player_exposure'] if p.name == 'Aaron Judge'), None)
        assert judge is not None
        assert judge.entry_count == 3
        assert judge.exposure_rate == 1.0  # 100%

    def test_team_exposure(self):
        """Test team exposure calculation."""
        calculator = ExposureCalculator()
        result = calculator.calculate_from_entries(SAMPLE_ENTRIES)

        # LAD should have high exposure
        lad = next((t for t in result['team_exposure'] if t.team == 'LAD'), None)
        assert lad is not None
        assert lad.total_players_owned > 0

    def test_overexposed_players(self):
        """Test finding overexposed players."""
        calculator = ExposureCalculator()
        overexposed = calculator.get_overexposed_players(SAMPLE_ENTRIES, threshold=0.5)

        # Aaron Judge is 100% exposed
        assert any(p.name == 'Aaron Judge' for p in overexposed)


class TestStackFinder:
    """Tests for StackFinder."""

    def test_find_stacks_in_entry(self):
        """Test stack finding in single entry."""
        finder = StackFinder()
        stacks = finder.find_stacks_in_entry(SAMPLE_ENTRIES[1])  # Has 3 LAD players

        # Should find LAD stack
        lad_stack = next((s for s in stacks if s.mlb_team == 'LAD'), None)
        assert lad_stack is not None
        assert lad_stack.stack_size == 3

    def test_analyze_stacks(self):
        """Test full stack analysis."""
        finder = StackFinder()
        result = finder.analyze_stacks(SAMPLE_ENTRIES)

        assert 'all_stacks' in result
        assert 'team_summaries' in result
        assert 'summary' in result

    def test_stack_summary(self):
        """Test stack summary statistics."""
        finder = StackFinder()
        result = finder.analyze_stacks(SAMPLE_ENTRIES)

        summary = result['summary']
        assert summary['total_entries'] == 3
        assert summary['total_stacks'] > 0

    def test_team_stacking_strategy(self):
        """Test team-specific stack analysis."""
        finder = StackFinder()
        strategy = finder.get_team_stacking_strategy(SAMPLE_ENTRIES, 'LAD')

        assert strategy['team'] == 'LAD'
        assert strategy['stack_count'] > 0

    def test_min_stack_size(self):
        """Test minimum stack size filter."""
        finder = StackFinder()

        # With min_size=3, should only find larger stacks
        result = finder.analyze_stacks(SAMPLE_ENTRIES, min_stack_size=3)

        for stack in result['all_stacks']:
            assert stack.stack_size >= 3


class TestIntegration:
    """Integration tests across modules."""

    def test_full_analysis_pipeline(self):
        """Test running all analyses together."""
        # Exposure
        exp_calc = ExposureCalculator()
        exposure = exp_calc.calculate_from_entries(SAMPLE_ENTRIES)

        # Correlations
        corr_analyzer = CorrelationAnalyzer()
        correlations = corr_analyzer.analyze_from_entries(SAMPLE_ENTRIES)

        # Stacks
        stack_finder = StackFinder()
        stacks = stack_finder.analyze_stacks(SAMPLE_ENTRIES)

        # All should return valid results
        assert len(exposure['player_exposure']) > 0
        assert len(correlations['pairs']) > 0
        assert len(stacks['all_stacks']) > 0

    def test_consistent_player_counts(self):
        """Test that player counts are consistent across analyses."""
        exp_calc = ExposureCalculator()
        exposure = exp_calc.calculate_from_entries(SAMPLE_ENTRIES)

        # Get unique players from entries
        all_players = set()
        for entry in SAMPLE_ENTRIES:
            for p in entry['players']:
                all_players.add(p['name'])

        # Should match exposure unique players
        assert len(exposure['player_exposure']) == len(all_players)
