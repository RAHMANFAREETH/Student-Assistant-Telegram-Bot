"""
V5.3 Navigation Migration Helper

Purpose:
Replace duplicated top-level GLOBAL_BUTTONS assignments
with:

    from navigation import GLOBAL_BUTTONS

The script creates a .bak_v5_3 backup before modifying
each file.

Run from your project folder:

    python migrate_global_buttons.py

You can restore a file manually from:
    filename.py.bak_v5_3
"""

from pathlib import Path
import ast
import shutil


TARGET_FILES = [
    "notes.py",
    "reminders.py",
    "translate.py",
    "subjects.py",
    "assignments.py",
    "study_materials.py",
    "timetable.py",
    "study_planner.py",
    "voice_notes.py",
    "language_tools.py",
    "flashcards.py",
    "quiz.py",
    "exam_planner.py",
    "attendance.py",
    "study_goals.py",
    "semesters.py",
    "grades_gpa.py",
    "global_search.py",
    "revision_planner.py",
    "study_streak.py",
    "notification_preferences.py",
]


def find_global_buttons_node(
    tree,
):
    for node in tree.body:
        if isinstance(
            node,
            ast.Assign,
        ):
            for target in node.targets:
                if (
                    isinstance(
                        target,
                        ast.Name,
                    )
                    and target.id
                    == "GLOBAL_BUTTONS"
                ):
                    return node

        if isinstance(
            node,
            ast.AnnAssign,
        ):
            target = node.target

            if (
                isinstance(
                    target,
                    ast.Name,
                )
                and target.id
                == "GLOBAL_BUTTONS"
            ):
                return node

    return None


def migrate_file(
    path,
):
    source = path.read_text(
        encoding="utf-8"
    )

    if (
        "from navigation import GLOBAL_BUTTONS"
        in source
    ):
        return (
            "already migrated"
        )

    try:
        tree = ast.parse(
            source
        )

    except SyntaxError as error:
        return (
            f"skipped — syntax error: {error}"
        )

    node = find_global_buttons_node(
        tree
    )

    if not node:
        return (
            "no GLOBAL_BUTTONS block found"
        )

    lines = source.splitlines(
        keepends=True
    )

    start = node.lineno - 1
    end = node.end_lineno

    replacement = (
        "from navigation import GLOBAL_BUTTONS\n"
    )

    new_source = (
        "".join(
            lines[
                :start
            ]
        )
        + replacement
        + "".join(
            lines[
                end:
            ]
        )
    )

    backup = path.with_name(
        path.name
        + ".bak_v5_3"
    )

    shutil.copy2(
        path,
        backup,
    )

    path.write_text(
        new_source,
        encoding="utf-8",
    )

    return (
        f"migrated — backup: {backup.name}"
    )


def main():
    project = Path.cwd()

    print(
        "Student Assistant Bot V5.3"
    )

    print(
        "Central GLOBAL_BUTTONS migration"
    )

    print(
        "================================"
    )

    for filename in TARGET_FILES:
        path = project / filename

        if not path.exists():
            print(
                f"SKIP {filename}: file not found"
            )
            continue

        result = migrate_file(
            path
        )

        print(
            f"{filename}: {result}"
        )

    print(
        "\nFinished."
    )

    print(
        "Now run:"
    )

    print(
        "python -m py_compile *.py"
    )


if __name__ == "__main__":
    main()
