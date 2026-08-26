"""Shared scraper loop state (first-run bootstrap scan).

Use `import scraper.state as bot_state` in other modules — not `from scraper.state import is_first_run`,
or is_first_run stays True forever after finish_initial_scan().
"""

is_first_run = True

def finish_initial_scan():
    """Marks the end of the first full pass (history seeding without notifications)."""
    global is_first_run
    is_first_run = False
