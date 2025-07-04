"""Snippet management system for Pasta."""

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Snippet:
    """Represents a text snippet.

    Attributes:
        id: Unique identifier for the snippet
        title: Human-readable title (alias for name)
        name: Human-readable name
        content: The actual text content
        category: Category for organization
        hotkey: Optional hotkey combination
        tags: List of tags for searching
        created_at: Creation timestamp
        updated_at: Last update timestamp
        use_count: Number of times used
        is_template: Whether this is a template snippet
    """

    content: str
    title: str = ""
    name: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = "general"
    hotkey: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    use_count: int = 0
    is_template: bool = False

    def __post_init__(self) -> None:
        """Initialize name and title fields.

        Ensures both name and title are set, using one to populate
        the other if needed, defaulting to 'Untitled' if both are empty.
        """
        # Support both title and name
        if self.title and not self.name:
            self.name = self.title
        elif self.name and not self.title:
            self.title = self.name
        elif not self.title and not self.name:
            self.name = self.title = "Untitled"

    def validate(self) -> bool:
        """Validate snippet data.

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if not self.name.strip():
            raise ValueError("Snippet name cannot be empty")

        if not self.content.strip():
            raise ValueError("Snippet content cannot be empty")

        if self.hotkey and not self._validate_hotkey(self.hotkey):
            raise ValueError(f"Invalid hotkey format: {self.hotkey}")

        return True

    def _validate_hotkey(self, hotkey: str) -> bool:
        """Validate hotkey format.

        Args:
            hotkey: Hotkey string to validate

        Returns:
            True if valid hotkey format
        """
        if not hotkey:
            return True

        # Basic hotkey validation (modifier+key format)
        pattern = r"^(ctrl|cmd|alt|shift)(\+(ctrl|cmd|alt|shift))*\+\w+$"
        return bool(re.match(pattern, hotkey.lower()))

    def to_dict(self) -> dict[str, Any]:
        """Convert snippet to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "name": self.name,
            "content": self.content,
            "category": self.category,
            "hotkey": self.hotkey,
            "tags": self.tags.copy(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "use_count": self.use_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Snippet":
        """Create snippet from dictionary.

        Args:
            data: Dictionary with snippet data

        Returns:
            Snippet instance
        """
        # Parse datetime strings
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        # Ensure tags is a list
        if "tags" in data and not isinstance(data["tags"], list):
            data["tags"] = []

        return cls(**data)

    def update(self, **kwargs: Any) -> None:
        """Update snippet fields.

        Args:
            **kwargs: Fields to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()

    def increment_use_count(self) -> None:
        """Increment the use count."""
        self.use_count += 1
        self.updated_at = datetime.now()


class SnippetManager:
    """Manages a collection of snippets.

    Attributes:
        snippets_path: Path to snippets storage file
        snippets: Dictionary of snippets by ID
    """

    def __init__(self, snippets_path: str | Path | None = None) -> None:
        """Initialize SnippetManager.

        Args:
            snippets_path: Path to snippets file (defaults to user config)
        """
        if snippets_path is None:
            # Use platform-appropriate config directory
            import platform

            system = platform.system()
            if system == "Darwin":  # macOS
                config_dir = Path.home() / "Library" / "Preferences" / "Pasta"
            elif system == "Windows":
                import os

                appdata = os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming"))
                config_dir = Path(appdata) / "Pasta"
            else:  # Linux/Unix
                config_dir = Path.home() / ".config" / "pasta"

            config_dir.mkdir(parents=True, exist_ok=True)
            self.snippets_path = config_dir / "snippets.json"
        else:
            self.snippets_path = Path(snippets_path)

        self.snippets: dict[str, Snippet] = {}
        self.load()

    def save_snippet(self, snippet: Snippet) -> str:
        """Save a snippet.

        Args:
            snippet: Snippet to save

        Returns:
            ID of saved snippet

        Raises:
            ValueError: If validation fails or hotkey conflict
        """
        snippet.validate()

        # Check hotkey conflict
        if snippet.hotkey:
            existing = self.get_snippet_by_hotkey(snippet.hotkey)
            if existing and existing.id != snippet.id:
                raise ValueError(f"Hotkey {snippet.hotkey} is already in use")

        # Generate ID if needed
        if not snippet.id:
            snippet.id = str(uuid.uuid4())

        self.snippets[snippet.id] = snippet
        self.save()
        return snippet.id

    def add_snippet(
        self,
        name: str,
        content: str,
        category: str = "general",
        hotkey: str = "",
        tags: list[str] | None = None,
    ) -> Snippet:
        """Add a new snippet.

        Args:
            name: Snippet name
            content: Snippet content
            category: Category for organization
            hotkey: Optional hotkey
            tags: Optional list of tags

        Returns:
            Created snippet

        Raises:
            ValueError: If validation fails or hotkey conflict
        """
        # Check hotkey uniqueness
        if hotkey:
            existing = self.get_snippet_by_hotkey(hotkey)
            if existing:
                raise ValueError(f"Hotkey {hotkey} is already in use by '{existing.name}'")

        snippet = Snippet(
            name=name,
            content=content,
            category=category,
            hotkey=hotkey,
            tags=tags or [],
        )
        snippet.validate()

        self.snippets[snippet.id] = snippet
        self.save()
        return snippet

    def get_snippet(self, snippet_id: str) -> Snippet | None:
        """Get snippet by ID.

        Args:
            snippet_id: Snippet ID

        Returns:
            Snippet or None if not found
        """
        return self.snippets.get(snippet_id)

    def update_snippet(self, snippet_id: str, **kwargs: Any) -> Snippet | None:
        """Update an existing snippet.

        Args:
            snippet_id: ID of snippet to update
            **kwargs: Fields to update

        Returns:
            Updated snippet or None if not found

        Raises:
            ValueError: If validation fails or hotkey conflict
        """
        snippet = self.get_snippet(snippet_id)
        if not snippet:
            return None

        # Check hotkey uniqueness if updating hotkey
        if "hotkey" in kwargs and kwargs["hotkey"]:
            existing = self.get_snippet_by_hotkey(kwargs["hotkey"])
            if existing and existing.id != snippet_id:
                raise ValueError(f"Hotkey {kwargs['hotkey']} is already in use by '{existing.name}'")

        snippet.update(**kwargs)
        snippet.validate()
        self.save()
        return snippet

    def delete_snippet(self, snippet_id: str) -> bool:
        """Delete a snippet.

        Args:
            snippet_id: ID of snippet to delete

        Returns:
            True if deleted, False if not found
        """
        if snippet_id in self.snippets:
            del self.snippets[snippet_id]
            self.save()
            return True
        return False

    def get_all_snippets(self) -> list[Snippet]:
        """Get all snippets.

        Returns:
            List of all snippets
        """
        return list(self.snippets.values())

    def get_snippets_by_category(self, category: str) -> list[Snippet]:
        """Get snippets by category.

        Args:
            category: Category to filter by

        Returns:
            List of snippets in category
        """
        return [s for s in self.snippets.values() if s.category == category]

    def search_snippets_by_tag(self, tag: str) -> list[Snippet]:
        """Search snippets by tag.

        Args:
            tag: Tag to search for

        Returns:
            List of matching snippets
        """
        tag_lower = tag.lower()
        return [s for s in self.snippets.values() if any(tag_lower in t.lower() for t in s.tags)]

    def check_hotkey_conflict(self, hotkey: str) -> list[Snippet]:
        """Check for hotkey conflicts.

        Args:
            hotkey: Hotkey to check

        Returns:
            List of snippets using this hotkey
        """
        return [s for s in self.snippets.values() if s.hotkey == hotkey]

    def get_all_categories(self) -> list[str]:
        """Get all unique categories.

        Returns:
            List of category names
        """
        return self.get_categories()

    def delete_snippets(self, snippet_ids: list[str]) -> int:
        """Delete multiple snippets.

        Args:
            snippet_ids: List of IDs to delete

        Returns:
            Number deleted
        """
        return self.bulk_delete(snippet_ids)

    def delete_snippets_by_category(self, category: str) -> int:
        """Delete all snippets in a category.

        Args:
            category: Category to delete

        Returns:
            Number deleted
        """
        to_delete = [s.id for s in self.snippets.values() if s.category == category]
        return self.delete_snippets(to_delete)

    def register_snippet_hotkeys(self, hotkey_manager: Any) -> None:  # noqa: ARG002
        """Register hotkeys for all snippets.

        Args:
            hotkey_manager: HotkeyManager to register with
        """
        for snippet in self.snippets.values():
            if snippet.hotkey:
                # In a real implementation, would register with hotkey manager
                pass

    def render_template(self, snippet_id: str, variables: dict[str, str]) -> str:
        """Render a template snippet.

        Args:
            snippet_id: ID of template snippet
            variables: Variables to substitute

        Returns:
            Rendered content
        """
        snippet = self.get_snippet(snippet_id)
        if not snippet:
            raise ValueError(f"Snippet {snippet_id} not found")

        content = snippet.content
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", value)
        return content

    def record_usage(self, snippet_id: str) -> None:
        """Record usage of a snippet.

        Args:
            snippet_id: ID of snippet used
        """
        self.use_snippet(snippet_id)

    def get_usage_stats(self) -> dict[str, dict[str, int]]:
        """Get usage statistics.

        Returns:
            Dictionary of snippet ID to usage stats
        """
        return {s.id: {"usage_count": s.use_count} for s in self.snippets.values()}

    def get_most_used_snippets(self, limit: int = 10) -> list[Snippet]:
        """Get most used snippets.

        Args:
            limit: Maximum number to return

        Returns:
            List of snippets sorted by usage
        """
        return self.get_recent_snippets(limit)

    def export_snippets(self, path: str | Path) -> None:
        """Export snippets to file.

        Args:
            path: Path to export file
        """
        path = Path(path)
        data = {
            "version": 1,
            "exported_at": datetime.now().isoformat(),
            "snippets": [snippet.to_dict() for snippet in self.snippets.values()],
        }
        path.write_text(json.dumps(data, indent=2))

    def import_snippets(self, path: str | Path, merge: bool = True) -> int:
        """Import snippets from file.

        Args:
            path: Path to import file
            merge: If True, keep existing snippets unchanged; if False, overwrite all

        Returns:
            Number of snippets imported

        Raises:
            ValueError: If import file is invalid
        """
        path = Path(path)
        try:
            data = json.loads(path.read_text())
            imported = 0

            if not merge:
                self.snippets.clear()

            for snippet_data in data.get("snippets", []):
                snippet = Snippet.from_dict(snippet_data)
                imported += 1

                # If merging and snippet exists, skip updating it
                if merge and snippet.id in self.snippets:
                    continue  # Skip but still count

                # Add/update snippet
                self.snippets[snippet.id] = snippet

            self.save()
            return imported
        except Exception as e:
            raise ValueError(f"Failed to import snippets: {e}") from e

    def search_snippets(self, query: str) -> list[Snippet]:
        """Search snippets by name, content, or tags.

        Args:
            query: Search query

        Returns:
            List of matching snippets
        """
        query_lower = query.lower()
        results = []

        for snippet in self.snippets.values():
            # Search in name
            if query_lower in snippet.name.lower():
                results.append(snippet)
                continue

            # Search in content
            if query_lower in snippet.content.lower():
                results.append(snippet)
                continue

            # Search in tags
            if any(query_lower in tag.lower() for tag in snippet.tags):
                results.append(snippet)

        return results

    def get_snippet_by_hotkey(self, hotkey: str) -> Snippet | None:
        """Get snippet by hotkey.

        Args:
            hotkey: Hotkey to search for

        Returns:
            Snippet or None if not found
        """
        for snippet in self.snippets.values():
            if snippet.hotkey == hotkey:
                return snippet
        return None

    def get_recent_snippets(self, limit: int = 10) -> list[Snippet]:
        """Get recently used snippets.

        Args:
            limit: Maximum number of snippets to return

        Returns:
            List of snippets sorted by use count
        """
        sorted_snippets = sorted(self.snippets.values(), key=lambda s: s.use_count, reverse=True)
        return sorted_snippets[:limit]

    def use_snippet(self, snippet_id: str) -> None:
        """Mark snippet as used (increment use count).

        Args:
            snippet_id: ID of snippet that was used
        """
        snippet = self.get_snippet(snippet_id)
        if snippet:
            snippet.increment_use_count()
            self.save()

    def get_categories(self) -> list[str]:
        """Get all unique categories.

        Returns:
            List of category names
        """
        categories = set()
        for snippet in self.snippets.values():
            categories.add(snippet.category)
        return sorted(categories)

    def bulk_delete(self, snippet_ids: list[str]) -> int:
        """Delete multiple snippets.

        Args:
            snippet_ids: List of snippet IDs to delete

        Returns:
            Number of snippets deleted
        """
        deleted = 0
        for snippet_id in snippet_ids:
            if snippet_id in self.snippets:
                del self.snippets[snippet_id]
                deleted += 1

        if deleted > 0:
            self.save()
        return deleted

    def bulk_update_category(self, snippet_ids: list[str], category: str) -> int:
        """Update category for multiple snippets.

        Args:
            snippet_ids: List of snippet IDs
            category: New category

        Returns:
            Number of snippets updated
        """
        updated = 0
        for snippet_id in snippet_ids:
            snippet = self.get_snippet(snippet_id)
            if snippet:
                snippet.category = category
                snippet.updated_at = datetime.now()
                updated += 1

        if updated > 0:
            self.save()
        return updated

    def create_snippet_template(self, name: str, content: str, category: str = "templates") -> Snippet:
        """Create a snippet template with variables.

        Args:
            name: Template name
            content: Template content with {variables}
            category: Category (defaults to "templates")

        Returns:
            Created template snippet
        """
        return self.add_snippet(name, content, category, tags=["template"])

    def create_from_template(self, template_id: str, name: str, variables: dict[str, str]) -> Snippet:
        """Create snippet from template with variable substitution.

        Args:
            template_id: ID of template snippet
            name: Name for new snippet
            variables: Dictionary of variable substitutions

        Returns:
            Created snippet

        Raises:
            ValueError: If template not found
        """
        template = self.get_snippet(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Substitute variables
        content = template.content
        for var_name, var_value in variables.items():
            content = content.replace(f"{{{var_name}}}", var_value)

        return self.add_snippet(name, content, category=template.category)

    def save(self) -> None:
        """Save snippets to file."""
        data = {
            "version": 1,
            "snippets": [snippet.to_dict() for snippet in self.snippets.values()],
        }
        self.snippets_path.write_text(json.dumps(data, indent=2))

    def load(self) -> None:
        """Load snippets from file."""
        if not self.snippets_path.exists():
            return

        try:
            data = json.loads(self.snippets_path.read_text())
            self.snippets.clear()

            for snippet_data in data.get("snippets", []):
                snippet = Snippet.from_dict(snippet_data)
                self.snippets[snippet.id] = snippet
        except Exception as e:
            print(f"Error loading snippets: {e}")
