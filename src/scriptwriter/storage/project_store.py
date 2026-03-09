from __future__ import annotations

from typing import Protocol

from scriptwriter.projects.repository import ProjectRepository


class ProjectStore(ProjectRepository, Protocol):
    """Storage contract for project-centric state and version persistence."""
