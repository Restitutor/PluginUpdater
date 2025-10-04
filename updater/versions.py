import re
from functools import total_ordering
from typing import Self

from packaging.version import InvalidVersion, Version


@total_ordering
class CustomVersion:
    """A version class that handles complex version strings with suffixes."""

    # Comprehensive regex to extract version components
    VERSION_PATTERN = re.compile(
        r"^(?P<version>\d+(?:\.\d+)*)"  # Core version numbers
        r"(?:\.(?P<build>\d+))?"  # Optional build number after last dot
        r"(?P<suffix>.*?)$",  # Everything else is suffix
    )

    def __init__(self, version_string: str) -> None:
        # We rewrite because these have no semantic value
        for suffix in ("-SNAPSHOT", ";HEAD", "-Premium"):
            version_string = version_string.replace(suffix, "")

        self.original = version_string.strip()
        self.suffix = ""
        self.core_version: Version = self._parse()

    def _parse(self) -> Version:
        """Parse the version string into components."""
        # Handle special case: extract build number from patterns like "(build #217)"
        build_match = re.search(r"\(build\s*#?(\d+)\)", self.original)
        normalized = self.original

        if build_match:
            # Replace build pattern with dot notation for easier parsing
            build_num = build_match.group(1)
            normalized = (
                self.original[: build_match.start()]
                + f".{build_num}"
                + self.original[build_match.end() :]
            )

        # Extract version components
        match = self.VERSION_PATTERN.match(normalized)
        if not match:
            # Fallback: try to find any numeric sequence
            fallback = re.search(r"(\d+(?:\.\d+)*)", self.original)
            if fallback:
                version_str = fallback.group(1)
                suffix_start = fallback.end()
                self.suffix = self.original[suffix_start:].strip()
            else:
                # No version numbers found at all
                version_str = "0.0.0"
                self.suffix = self.original
        else:
            version_str = match.group("version")
            if match.group("build"):
                version_str += "." + match.group("build")
            self.suffix = match.group("suffix").strip()

        # Clean up common suffix patterns
        self.suffix = re.sub(r"^[-;,\s]+", "", self.suffix)  # Remove leading separators

        # Try to parse the version
        try:
            return Version(version_str)
        except InvalidVersion:
            # If parsing fails, use a zero version
            self.suffix = self.original  # Treat entire string as suffix
            return Version("0.0.0")

    def _comparison_key(self) -> tuple[Version, str]:
        """Generate a comparison key for sorting."""
        # First compare by core version then by suffix text
        return (
            self.core_version,
            self.suffix.lower() if self.suffix else "",
        )

    def __eq__(self, other: object) -> bool:
        """Check equality with another CustomVersion."""
        if not isinstance(other, CustomVersion):
            return NotImplemented
        return self._comparison_key() == other._comparison_key()

    def __lt__(self, other: object) -> bool:
        """Compare with another CustomVersion."""
        if not isinstance(other, CustomVersion):
            return NotImplemented
        return self._comparison_key() < other._comparison_key()

    def __str__(self) -> str:
        """Return the original version string."""
        return self.original

    def __repr__(self) -> str:
        """Return a detailed representation."""
        return f"CustomVersion('{self.original}', core={self.core_version}, suffix='{self.suffix}')"

    def is_major_upgrade(self, other: Self) -> bool:
        """Check if this version is a major upgrade from another."""
        try:
            return (
                self.core_version.major > other.core_version.major
                and other.core_version.major > 0
            )
        except AttributeError:
            return False
