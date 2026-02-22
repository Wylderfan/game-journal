"""
flask db-backup  — dump the MySQL database to a timestamped .sql file
flask db-restore — restore the database from a .sql file
"""
import os
import subprocess
import sys
from datetime import datetime
from urllib.parse import urlparse

import click
from flask.cli import with_appcontext


def _parse_db_url():
    """Parse DATABASE_URL and return a dict of connection components."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        click.echo("ERROR: DATABASE_URL is not set.", err=True)
        sys.exit(1)

    parsed = urlparse(url)
    return {
        "host":     parsed.hostname or "127.0.0.1",
        "port":     str(parsed.port or 3306),
        "user":     parsed.username or "",
        "password": parsed.password or "",
        "dbname":   parsed.path.lstrip("/"),
    }


@click.command("db-backup")
@click.option(
    "--output-dir",
    default="backups",
    show_default=True,
    help="Directory to write the backup file into.",
)
@with_appcontext
def backup_command(output_dir):
    """Dump the database to a timestamped SQL file."""
    db = _parse_db_url()

    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"{db['dbname']}_{timestamp}.sql")

    cmd = [
        "mysqldump",
        f"--host={db['host']}",
        f"--port={db['port']}",
        f"--user={db['user']}",
        f"--password={db['password']}",
        "--single-transaction",
        "--routines",
        "--triggers",
        db["dbname"],
    ]

    click.echo(f"Backing up '{db['dbname']}' → {filename} ...")
    try:
        with open(filename, "w") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            os.remove(filename)
            click.echo(f"ERROR: mysqldump failed:\n{result.stderr}", err=True)
            sys.exit(1)
    except FileNotFoundError:
        click.echo("ERROR: mysqldump not found. Install MySQL client tools.", err=True)
        sys.exit(1)

    size_kb = os.path.getsize(filename) / 1024
    click.echo(f"Done. ({size_kb:.1f} KB)")


@click.command("db-restore")
@click.argument("filepath")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
@with_appcontext
def restore_command(filepath, yes):
    """Restore the database from a SQL backup file."""
    if not os.path.isfile(filepath):
        click.echo(f"ERROR: File not found: {filepath}", err=True)
        sys.exit(1)

    db = _parse_db_url()

    if not yes:
        click.confirm(
            f"This will overwrite '{db['dbname']}' with data from {filepath}. Continue?",
            abort=True,
        )

    cmd = [
        "mysql",
        f"--host={db['host']}",
        f"--port={db['port']}",
        f"--user={db['user']}",
        f"--password={db['password']}",
        db["dbname"],
    ]

    click.echo(f"Restoring '{db['dbname']}' from {filepath} ...")
    try:
        with open(filepath, "r") as f:
            result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            click.echo(f"ERROR: mysql restore failed:\n{result.stderr}", err=True)
            sys.exit(1)
    except FileNotFoundError:
        click.echo("ERROR: mysql client not found. Install MySQL client tools.", err=True)
        sys.exit(1)

    click.echo("Done.")
