# tests/test_analysis.py — Unit tests for analysis module
import pytest
from db.analysis import (
    add_analysis,
    list_analysis,
    get_analysis,
    update_analysis,
    delete_analysis,
    add_analysis_stage,
    get_analysis_stage,
    list_analysis_stages,
    update_analysis_stage,
    delete_analysis_stage,
)


class TestAddAnalysis:
    def test_add_analysis_basic(self, test_user):
        """Test creating a basic analysis."""
        analysis_id = add_analysis(test_user, {
            "date_local": "2026-02-01",
            "asset": "EUR/USD",
        })
        assert analysis_id is not None
        assert analysis_id > 0

    def test_add_analysis_all_fields(self, test_user):
        """Test creating analysis with all fields."""
        analysis_id = add_analysis(test_user, {
            "date_local": "2026-02-01",
            "asset": "GBP/USD",
            "daily_bias": "Bullish",
            "fact_bias": "Bullish",
            "day_result": "profit",
            "state": "post-market",
        })

        analysis = get_analysis(analysis_id, test_user)
        assert analysis["asset"] == "GBP/USD"
        assert analysis["daily_bias"] == "Bullish"
        assert analysis["day_result"] == "profit"

    def test_add_analysis_missing_date_raises(self, test_user):
        """Test creating analysis without date raises error."""
        with pytest.raises(ValueError, match="date_local"):
            add_analysis(test_user, {"asset": "EUR/USD"})


class TestListAnalysis:
    def test_list_empty(self, test_user):
        """Test listing when no analysis exist."""
        analyses = list_analysis(test_user)
        assert analyses == []

    def test_list_analysis(self, test_user):
        """Test listing multiple analyses."""
        add_analysis(test_user, {"date_local": "2026-02-01"})
        add_analysis(test_user, {"date_local": "2026-02-02"})

        analyses = list_analysis(test_user)
        assert len(analyses) == 2

    def test_filter_by_asset(self, test_user):
        """Test filtering by asset."""
        add_analysis(test_user, {"date_local": "2026-02-01", "asset": "EUR/USD"})
        add_analysis(test_user, {"date_local": "2026-02-02", "asset": "GBP/USD"})
        add_analysis(test_user, {"date_local": "2026-02-03", "asset": "EUR/USD"})

        analyses = list_analysis(test_user, {"asset": "EUR/USD"})
        assert len(analyses) == 2

    def test_filter_by_date_range(self, test_user):
        """Test filtering by date range."""
        add_analysis(test_user, {"date_local": "2026-01-15"})
        add_analysis(test_user, {"date_local": "2026-02-01"})
        add_analysis(test_user, {"date_local": "2026-02-15"})

        analyses = list_analysis(test_user, {
            "date_from": "2026-02-01",
            "date_to": "2026-02-10",
        })
        assert len(analyses) == 1


class TestGetAnalysis:
    def test_get_existing(self, test_user):
        """Test getting an existing analysis."""
        analysis_id = add_analysis(test_user, {
            "date_local": "2026-02-01",
            "asset": "XAU/USD",
            "daily_bias": "Bearish",
        })
        analysis = get_analysis(analysis_id, test_user)

        assert analysis is not None
        assert analysis["asset"] == "XAU/USD"
        assert analysis["daily_bias"] == "Bearish"

    def test_get_nonexistent(self, test_user):
        """Test getting a non-existent analysis."""
        analysis = get_analysis(99999, test_user)
        assert analysis is None


class TestUpdateAnalysis:
    def test_update_bias(self, test_user):
        """Test updating analysis bias."""
        analysis_id = add_analysis(test_user, {
            "date_local": "2026-02-01",
            "daily_bias": "Bullish",
        })
        update_analysis(analysis_id, test_user, {"fact_bias": "Bearish"})

        analysis = get_analysis(analysis_id, test_user)
        assert analysis["fact_bias"] == "Bearish"

    def test_update_nonexistent_raises(self, test_user):
        """Update invalid analysis ID raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            update_analysis(99999, test_user, {"daily_bias": "Bullish"})


class TestDeleteAnalysis:
    def test_delete_analysis(self, test_user):
        """Test deleting an analysis."""
        analysis_id = add_analysis(test_user, {"date_local": "2026-02-01"})
        delete_analysis(analysis_id, test_user)

        assert get_analysis(analysis_id, test_user) is None

    def test_delete_nonexistent_raises(self, test_user):
        """Delete invalid analysis ID raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            delete_analysis(99999, test_user)


class TestAnalysisStages:
    def test_add_stage(self, test_user):
        """Test adding analysis stage."""
        analysis_id = add_analysis(test_user, {"date_local": "2026-02-01"})
        stage_id = add_analysis_stage({
            "analysis_id": analysis_id,
            "type": "pre-market",
            "summary": "Morning analysis",
        })

        assert stage_id is not None
        assert stage_id > 0

    def test_get_stage(self, test_user):
        """Test getting analysis stage."""
        analysis_id = add_analysis(test_user, {"date_local": "2026-02-01", "asset": "EUR/USD"})
        stage_id = add_analysis_stage({
            "analysis_id": analysis_id,
            "type": "plan",
            "summary": "Trading plan",
        })

        stage = get_analysis_stage(stage_id)
        assert stage is not None
        assert stage["type"] == "plan"
        assert stage["summary"] == "Trading plan"
        assert stage["asset"] == "EUR/USD"  # Joined from analysis

    def test_list_stages_by_analysis(self, test_user):
        """Test listing stages filtered by analysis."""
        a1 = add_analysis(test_user, {"date_local": "2026-02-01"})
        a2 = add_analysis(test_user, {"date_local": "2026-02-02"})

        add_analysis_stage({"analysis_id": a1, "type": "pre-market"})
        add_analysis_stage({"analysis_id": a1, "type": "plan"})
        add_analysis_stage({"analysis_id": a2, "type": "pre-market"})

        stages = list_analysis_stages(test_user, {"analysis_id": a1})
        assert len(stages) == 2

    def test_update_stage(self, test_user):
        """Test updating analysis stage."""
        analysis_id = add_analysis(test_user, {"date_local": "2026-02-01"})
        stage_id = add_analysis_stage({
            "analysis_id": analysis_id,
            "type": "pre-market",
            "summary": "Original",
        })

        update_analysis_stage(stage_id, {"summary": "Updated"})

        stage = get_analysis_stage(stage_id)
        assert stage["summary"] == "Updated"

    def test_delete_stage(self, test_user):
        """Test deleting analysis stage."""
        analysis_id = add_analysis(test_user, {"date_local": "2026-02-01"})
        stage_id = add_analysis_stage({
            "analysis_id": analysis_id,
            "type": "pre-market",
        })

        delete_analysis_stage(stage_id)
        assert get_analysis_stage(stage_id) is None
