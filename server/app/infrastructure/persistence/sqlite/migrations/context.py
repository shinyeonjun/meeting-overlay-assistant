"""계정/컨텍스트/워크스페이스 마이그레이션."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from server.app.core.workspace_defaults import (
    DEFAULT_WORKSPACE_ID,
    DEFAULT_WORKSPACE_NAME,
    DEFAULT_WORKSPACE_SLUG,
    DEFAULT_WORKSPACE_STATUS,
)


def migrate_meeting_context_tables(connection: sqlite3.Connection) -> None:
    """계정/연락처/업무 흐름 테이블을 준비한다."""

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_by_user_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
            FOREIGN KEY(created_by_user_id) REFERENCES users(id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS contacts (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            account_id TEXT,
            name TEXT NOT NULL,
            email TEXT,
            job_title TEXT,
            department TEXT,
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_by_user_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
            FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE SET NULL,
            FOREIGN KEY(created_by_user_id) REFERENCES users(id)
        )
        """
    )
    contact_columns = {row["name"] for row in connection.execute("PRAGMA table_info(contacts)").fetchall()}
    if "department" not in contact_columns:
        connection.execute("ALTER TABLE contacts ADD COLUMN department TEXT")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS context_threads (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            account_id TEXT,
            contact_id TEXT,
            title TEXT NOT NULL,
            summary TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_by_user_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
            FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE SET NULL,
            FOREIGN KEY(contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
            FOREIGN KEY(created_by_user_id) REFERENCES users(id)
        )
        """
    )


def migrate_workspaces_and_memberships(connection: sqlite3.Connection) -> None:
    """기본 워크스페이스와 사용자 멤버십을 준비한다."""

    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS workspaces (
            id TEXT PRIMARY KEY,
            slug TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_members (
            workspace_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            workspace_role TEXT NOT NULL DEFAULT 'member',
            status TEXT NOT NULL DEFAULT 'active',
            joined_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (workspace_id, user_id),
            FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        INSERT INTO workspaces (id, slug, name, status, created_at, updated_at)
        SELECT ?, ?, ?, ?, ?, ?
        WHERE NOT EXISTS (SELECT 1 FROM workspaces WHERE id = ?)
        """,
        (
            DEFAULT_WORKSPACE_ID,
            DEFAULT_WORKSPACE_SLUG,
            DEFAULT_WORKSPACE_NAME,
            DEFAULT_WORKSPACE_STATUS,
            now,
            now,
            DEFAULT_WORKSPACE_ID,
        ),
    )

    user_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(users)").fetchall()
    }
    user_select_fields = ["id", "status", "created_at", "updated_at"]
    if "role" in user_columns:
        user_select_fields.insert(1, "role")

    users_without_membership = connection.execute(
        f"""
        SELECT {", ".join(user_select_fields)}
        FROM users
        WHERE NOT EXISTS (
            SELECT 1
            FROM workspace_members
            WHERE workspace_members.user_id = users.id
        )
        """
    ).fetchall()
    for row in users_without_membership:
        role_value = row["role"] if "role" in row.keys() else None
        workspace_role = (
            role_value
            if role_value in {"owner", "admin", "member", "viewer"}
            else "member"
        )
        membership_status = "active" if row["status"] == "active" else "inactive"
        joined_at = row["created_at"] or now
        updated_at = row["updated_at"] or joined_at
        connection.execute(
            """
            INSERT INTO workspace_members (
                workspace_id,
                user_id,
                workspace_role,
                status,
                joined_at,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                DEFAULT_WORKSPACE_ID,
                row["id"],
                workspace_role,
                membership_status,
                joined_at,
                joined_at,
                updated_at,
            ),
        )
