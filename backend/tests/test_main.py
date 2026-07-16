from app.main import validate_project_title
import pytest


def test_valid_project_title_is_trimmed() -> None:
    assert validate_project_title("  ResearchHub  ") == "ResearchHub"


@pytest.mark.parametrize("title", ["", "  ", "AI", "Hi"])
def test_short_project_titles_are_rejected(title: str) -> None:
    with pytest.raises(ValueError):
        validate_project_title(title)
