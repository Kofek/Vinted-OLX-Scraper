"""Shared scraper loop state (first-run bootstrap scan)."""

is_first_run = True


def finish_initial_scan():
    """Marks the end of the first full pass (history seeding without notifications)."""
    global is_first_run
    is_first_run = False
