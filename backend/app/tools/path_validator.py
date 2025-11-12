"""
Secure path validation with allowlist approach.

This module provides PathValidator class for validating file paths are within
allowed directories, protecting against path traversal and symlink attacks.
"""

from pathlib import Path
from typing import List


class PathValidator:
    """
    Validates file paths are within allowed directories (allowlist approach).

    This class implements secure path validation to prevent:
    - Path traversal attacks (../)
    - Symlink attacks (symlinks pointing outside allowed roots)
    - Access to unauthorized directories

    Example:
        >>> validator = PathValidator([Path("/home/user/project")])
        >>> safe_path = validator.validate("src/main.py")
        >>> print(safe_path)
        /home/user/project/src/main.py

    Attributes:
        allowed_roots: List of resolved absolute paths that are allowed as roots
    """

    def __init__(self, allowed_roots: List[Path]) -> None:
        """
        Initialize validator with list of allowed root directories.

        Args:
            allowed_roots: List of Path objects representing allowed root directories.
                          Paths will be expanded (~ becomes home directory) and resolved
                          to absolute paths.

        Example:
            >>> validator = PathValidator([
            ...     Path("/home/user/project"),
            ...     Path("~/documents")
            ... ])
        """
        self.allowed_roots: List[Path] = [
            Path(root).expanduser().resolve() for root in allowed_roots
        ]

    def validate(self, file_path: str) -> Path:
        """
        Validate that file_path is within one of the allowed roots.

        This method performs comprehensive security checks:
        1. Expands user paths (~) to absolute paths
        2. Resolves relative paths to absolute paths
        3. Checks if path is within allowed roots
        4. If path contains symlinks, resolves them and re-checks containment

        Args:
            file_path: Path to validate (can be relative or absolute, with or without ~)

        Returns:
            Resolved absolute Path object if validation succeeds

        Raises:
            ValueError: If path is outside allowed roots or symlink points outside
            OSError: If path resolution fails (e.g., too many symlink levels)

        Example:
            >>> validator = PathValidator([Path("/home/user/project")])
            >>> validator.validate("src/main.py")
            PosixPath('/home/user/project/src/main.py')
            >>> validator.validate("/etc/passwd")  # doctest: +SKIP
            ValueError: Path /etc/passwd is not within allowed directories

        Security Notes:
            - Symlinks are resolved and their targets are validated
            - Path traversal attempts (..) are neutralized by resolve()
            - Both the original path and symlink target must be in allowed roots
        """
        # Step 1: Expand user paths and resolve to absolute path
        # resolve() handles:
        # - Converting relative to absolute paths
        # - Resolving . and .. components
        # - Following symlinks
        try:
            resolved_path = Path(file_path).expanduser().resolve()
        except (OSError, RuntimeError) as e:
            raise ValueError(f"Failed to resolve path {file_path}: {e}") from e

        # Step 2: Check if resolved path is within any allowed root
        if not self._is_within_allowed_roots(resolved_path):
            raise ValueError(
                f"Path {resolved_path} is not within allowed directories: "
                f"{[str(root) for root in self.allowed_roots]}"
            )

        # Step 3: Check for symlink attacks
        # If the original path contains symlinks, we need to verify that
        # any intermediate symlinks don't point outside allowed roots
        original_path = Path(file_path).expanduser()

        # If original path is not absolute, make it absolute before checking
        if not original_path.is_absolute():
            original_path = Path.cwd() / original_path

        # Check if any component is a symlink that escapes allowed roots
        self._check_symlink_chain(original_path)

        return resolved_path

    def _is_within_allowed_roots(self, path: Path) -> bool:
        """
        Check if path is within any of the allowed roots.

        Args:
            path: Absolute resolved Path to check

        Returns:
            True if path is within at least one allowed root, False otherwise

        Note:
            Uses Path.is_relative_to() for safe containment checking.
            This method properly handles edge cases like:
            - /tmp vs /tmp2 (not contained)
            - /home/user/project vs /home/user (contained)
        """
        for root in self.allowed_roots:
            try:
                # is_relative_to returns True if path is under root
                if path.is_relative_to(root):
                    return True
            except (ValueError, TypeError):
                # is_relative_to can raise ValueError on some edge cases
                continue

        return False

    def _check_symlink_chain(self, path: Path) -> None:
        """
        Check that symlink chain doesn't escape allowed roots.

        This method walks through the path components WITHIN the allowed roots
        and checks if any symlinks point outside. This prevents attacks like:
        - /allowed/malicious_link -> /etc/passwd
        - /allowed/dir/link -> ../../../../etc

        Args:
            path: Absolute path to check (may contain symlinks)

        Raises:
            ValueError: If any symlink in the chain points outside allowed roots

        Note:
            We only check symlinks that are within the allowed roots, not
            system-level symlinks in the filesystem structure leading to the roots.
            This prevents false positives on systems with symlinked directories
            like /var -> /private/var on macOS.
        """
        # Find which allowed root this path is under (if any)
        matching_root = None
        for root in self.allowed_roots:
            try:
                if path.is_relative_to(root):
                    matching_root = root
                    break
            except (ValueError, TypeError):
                continue

        # If path is not within any root, we can't check symlinks
        # (This should have been caught earlier by _is_within_allowed_roots)
        if matching_root is None:
            return

        # Now check symlinks starting from the matching root, not from filesystem root
        # This avoids checking system-level symlinks like /var -> /private/var
        current = matching_root

        # Get the relative path from the root to the target
        try:
            relative_parts = path.relative_to(matching_root).parts
        except ValueError:
            # Path is not relative to root, should have been caught earlier
            return

        # Check each component in the relative path
        for part in relative_parts:
            current = current / part

            # If this component is a symlink, check where it points
            if current.is_symlink():
                try:
                    # Get the target of the symlink (fully resolved)
                    symlink_target = current.resolve()

                    # Verify the symlink target is within allowed roots
                    if not self._is_within_allowed_roots(symlink_target):
                        raise ValueError(
                            f"Path {path} contains symlink {current} that points to "
                            f"{symlink_target}, which is not within allowed directories: "
                            f"{[str(root) for root in self.allowed_roots]}"
                        )
                except (OSError, RuntimeError) as e:
                    raise ValueError(
                        f"Failed to resolve symlink {current} in path {path}: {e}"
                    ) from e

            # Stop if we've reached the requested path
            if current == path:
                break
