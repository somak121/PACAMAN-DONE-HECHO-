"""Tests for ScoreTracker."""

from src.game.scoring import ScoreTracker


class TestScoreTracker:
    """Test suite for ScoreTracker."""

    def test_initial_score_is_zero(self) -> None:
        """Score should start at 0."""
        st = ScoreTracker()
        assert st.score == 0

    def test_pacgum_adds_correct_points(self) -> None:
        """Eating a pacgum should add the configured points."""
        st = ScoreTracker(points_per_pacgum=10)
        pts = st.add_pacgum()
        assert pts == 10
        assert st.score == 10

    def test_super_pacgum_adds_correct_points(self) -> None:
        """Eating a super-pacgum should add the configured points."""
        st = ScoreTracker(points_per_super_pacgum=50)
        pts = st.add_super_pacgum()
        assert pts == 50
        assert st.score == 50

    def test_ghost_adds_base_points(self) -> None:
        """First ghost in a combo should award base points."""
        st = ScoreTracker(points_per_ghost=200)
        pts = st.add_ghost()
        assert pts == 200
        assert st.score == 200

    def test_ghost_combo_doubles(self) -> None:
        """Sequential ghosts in one frightened phase should double points."""
        st = ScoreTracker(points_per_ghost=200)
        st.add_ghost()  # 200  (x1)
        pts2 = st.add_ghost()  # 400  (x2)
        pts3 = st.add_ghost()  # 800  (x4)
        assert pts2 == 400
        assert pts3 == 800
        assert st.score == 1400

    def test_ghost_combo_resets_on_super_pacgum(self) -> None:
        """Super-pacgum should reset the ghost combo multiplier."""
        st = ScoreTracker(points_per_ghost=200)
        st.add_ghost()
        st.add_ghost()  # combo = 2
        st.add_super_pacgum()  # reset combo
        pts = st.add_ghost()  # should be back to base 200
        assert pts == 200

    def test_ghost_combo_capped(self) -> None:
        """Ghost combo multiplier should cap at MAX_GHOST_MULTIPLIER."""
        st = ScoreTracker(points_per_ghost=200)
        for _ in range(20):
            st.add_ghost()
        # Last ghost should not exceed 200 * MAX_GHOST_MULTIPLIER = 1600
        max_pts = 200 * ScoreTracker.MAX_GHOST_MULTIPLIER
        last_pts = st.add_ghost()
        assert last_pts <= max_pts

    def test_score_never_negative(self) -> None:
        """Score should always be non-negative."""
        st = ScoreTracker()
        assert st.score >= 0

    def test_reset_clears_score(self) -> None:
        """Reset should bring score back to 0."""
        st = ScoreTracker()
        st.add_pacgum()
        st.add_ghost()
        st.reset()
        assert st.score == 0

    def test_reset_ghost_combo(self) -> None:
        """reset_ghost_combo should clear the multiplier."""
        st = ScoreTracker(points_per_ghost=200)
        st.add_ghost()
        st.add_ghost()
        st.reset_ghost_combo()
        pts = st.add_ghost()
        assert pts == 200

    def test_custom_point_values(self) -> None:
        """Custom point values from config should be respected."""
        st = ScoreTracker(
            points_per_pacgum=42,
            points_per_super_pacgum=100,
            points_per_ghost=500,
        )
        st.add_pacgum()
        st.add_super_pacgum()
        st.add_ghost()
        assert st.score == 42 + 100 + 500
