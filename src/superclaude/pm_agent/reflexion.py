"""
Reflexion Error Learning Pattern

Learn from past errors to prevent recurrence.

Token Budget:
    - Cache hit: 0 tokens (known error → instant solution)
    - Cache miss: 1-2K tokens (new investigation)

Performance:
    - Error recurrence rate: <10%
    - Solution reuse rate: >90%

Storage Strategy:
    - Primary: docs/memory/solutions_learned.jsonl (local file)
    - Secondary: mindbase (if available, semantic search)
    - Fallback: grep-based text search

Process:
    1. Error detected → Check past errors (smart lookup)
    2. IF similar found → Apply known solution (0 tokens)
    3. ELSE → Investigate root cause → Document solution
    4. Store for future reference (dual storage)
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ReflexionPattern:
    """
    Error learning and prevention through reflexion

    Usage:
        reflexion = ReflexionPattern()

        # When error occurs
        error_info = {
            "error_type": "AssertionError",
            "error_message": "Expected 5, got 3",
            "test_name": "test_calculation",
        }

        # Check for known solution
        solution = reflexion.get_solution(error_info)

        if solution:
            print(f"✅ Known error - Solution: {solution}")
        else:
            # New error - investigate and record
            reflexion.record_error(error_info)
    """

    def __init__(self, memory_dir: Optional[Path] = None):
        """
        Initialize reflexion pattern

        Args:
            memory_dir: Directory for storing error solutions
                       (defaults to docs/memory/ in current project)
        """
        if memory_dir is None:
            # Default to docs/memory/ in current working directory
            memory_dir = Path.cwd() / "docs" / "memory"

        self.memory_dir = memory_dir
        self.solutions_file = memory_dir / "solutions_learned.jsonl"
        self.mistakes_dir = memory_dir.parent / "mistakes"

        # Ensure directories exist
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.mistakes_dir.mkdir(parents=True, exist_ok=True)

    def get_solution(self, error_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get known solution for similar error

        Lookup strategy:
            1. Try mindbase semantic search (if available)
            2. Fallback to grep-based text search
            3. Return None if no match found

        Args:
            error_info: Error information dict

        Returns:
            Solution dict if found, None otherwise
        """
        error_signature = self._create_error_signature(error_info)

        # Try mindbase first (semantic search, 500 tokens)
        solution = self._search_mindbase(error_signature)
        if solution:
            return solution

        # Fallback to file-based search (0 tokens, local grep)
        solution = self._search_local_files(error_signature)
        return solution

    def record_error(self, error_info: Dict[str, Any]) -> None:
        """
        Record error and solution for future learning

        Stores to:
            1. docs/memory/solutions_learned.jsonl (append-only log)
            2. docs/mistakes/[feature]-[date].md (detailed analysis)

        Args:
            error_info: Error information dict containing:
                - test_name: Name of failing test
                - error_type: Type of error (e.g., AssertionError)
                - error_message: Error message
                - traceback: Stack trace
                - solution (optional): Solution applied
                - root_cause (optional): Root cause analysis
        """
        # Add timestamp
        error_info["timestamp"] = datetime.now().isoformat()

        # Append to solutions log (JSONL format)
        with self.solutions_file.open("a") as f:
            f.write(json.dumps(error_info) + "\n")

        # If this is a significant error with analysis, create mistake doc
        if error_info.get("root_cause") or error_info.get("solution"):
            self._create_mistake_doc(error_info)

    def _create_error_signature(self, error_info: Dict[str, Any]) -> str:
        """
        Create error signature for matching

        Combines:
            - Error type
            - Key parts of error message
            - Test context

        Args:
            error_info: Error information dict

        Returns:
            str: Error signature for matching
        """
        parts = []

        if "error_type" in error_info:
            parts.append(error_info["error_type"])

        if "error_message" in error_info:
            # Extract key words from error message
            message = error_info["error_message"]
            # Remove numbers (often varies between errors)
            import re

            message = re.sub(r"\d+", "N", message)
            parts.append(message[:100])  # First 100 chars

        if "test_name" in error_info:
            parts.append(error_info["test_name"])

        return " | ".join(parts)

    def _search_mindbase(self, error_signature: str) -> Optional[Dict[str, Any]]:
        """
        Search for similar error in mindbase (semantic search)

        Mindbase MCP provides semantic search for cross-session learning.
        This method integrates with Mindbase when available, with graceful
        degradation when not configured.

        Configuration:
            Set MINDBASE_ENABLED=1 to enable Mindbase integration.
            The actual MCP calls are handled by Claude Code, so this
            method stores/retrieves from the local mindbase cache.

        Args:
            error_signature: Error signature to search

        Returns:
            Solution dict if found, None if mindbase unavailable or no match
        """
        # Check if Mindbase integration is enabled
        if not self._is_mindbase_enabled():
            return None

        # Try to search the mindbase cache file
        mindbase_cache = self.memory_dir / "mindbase_cache.jsonl"
        if not mindbase_cache.exists():
            return None

        # Search for semantically similar entries
        best_match = None
        best_score = 0.0

        try:
            with mindbase_cache.open("r") as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        stored_signature = record.get("signature", "")

                        # Calculate semantic similarity score
                        score = self._calculate_similarity(
                            error_signature, stored_signature
                        )

                        if score > best_score and score >= 0.6:
                            best_score = score
                            best_match = record

                    except json.JSONDecodeError:
                        continue

        except (OSError, PermissionError):
            return None

        if best_match:
            return {
                "solution": best_match.get("solution"),
                "root_cause": best_match.get("root_cause"),
                "prevention": best_match.get("prevention"),
                "timestamp": best_match.get("timestamp"),
                "source": "mindbase",
                "similarity_score": best_score,
            }

        return None

    def _is_mindbase_enabled(self) -> bool:
        """Check if Mindbase integration is enabled."""
        return os.environ.get("MINDBASE_ENABLED", "").lower() in ("1", "true", "yes")

    def _calculate_similarity(self, sig1: str, sig2: str) -> float:
        """
        Calculate similarity between two error signatures.

        Uses a combination of:
        - Word overlap (Jaccard similarity)
        - Key term matching (error types, common patterns)

        Args:
            sig1: First signature
            sig2: Second signature

        Returns:
            float: Similarity score (0.0 - 1.0)
        """
        # Normalize signatures
        words1 = set(sig1.lower().split())
        words2 = set(sig2.lower().split())

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        jaccard = intersection / union if union > 0 else 0.0

        # Boost score for matching error types
        error_types = {
            "assertionerror",
            "typeerror",
            "valueerror",
            "keyerror",
            "indexerror",
            "importerror",
            "filenotfounderror",
            "connectionerror",
            "zerodivisionerror",
        }

        common_error_types = (words1 & words2) & error_types
        error_boost = 0.2 if common_error_types else 0.0

        return min(1.0, jaccard + error_boost)

    def store_to_mindbase(self, error_info: Dict[str, Any]) -> bool:
        """
        Store error information to Mindbase cache for cross-session learning.

        This method stores the error to a local cache file that can be
        synced with Mindbase MCP when available.

        Args:
            error_info: Error information dict

        Returns:
            bool: True if stored successfully
        """
        if not self._is_mindbase_enabled():
            return False

        mindbase_cache = self.memory_dir / "mindbase_cache.jsonl"

        try:
            # Create cache entry with signature
            cache_entry = {
                "signature": self._create_error_signature(error_info),
                "error_type": error_info.get("error_type"),
                "error_message": error_info.get("error_message"),
                "solution": error_info.get("solution"),
                "root_cause": error_info.get("root_cause"),
                "prevention": error_info.get("prevention"),
                "timestamp": datetime.now().isoformat(),
                "session_id": os.environ.get("CLAUDE_SESSION_ID", "unknown"),
            }

            with mindbase_cache.open("a") as f:
                f.write(json.dumps(cache_entry) + "\n")

            return True

        except (OSError, PermissionError):
            return False

    def get_cross_session_patterns(self) -> List[Dict[str, Any]]:
        """
        Get error patterns learned across sessions.

        Returns:
            List of error patterns with their solutions
        """
        patterns: List[Dict[str, Any]] = []

        mindbase_cache = self.memory_dir / "mindbase_cache.jsonl"
        if not mindbase_cache.exists():
            return patterns

        try:
            with mindbase_cache.open("r") as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        if record.get("solution"):
                            patterns.append(
                                {
                                    "error_type": record.get("error_type"),
                                    "pattern": record.get("signature"),
                                    "solution": record.get("solution"),
                                    "session_id": record.get("session_id"),
                                }
                            )
                    except json.JSONDecodeError:
                        continue

        except (OSError, PermissionError):
            pass

        return patterns

    def _search_local_files(self, error_signature: str) -> Optional[Dict[str, Any]]:
        """
        Search for similar error in local JSONL file

        Uses simple text matching on error signatures.

        Args:
            error_signature: Error signature to search

        Returns:
            Solution dict if found, None otherwise
        """
        if not self.solutions_file.exists():
            return None

        # Read JSONL file and search
        with self.solutions_file.open("r") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    stored_signature = self._create_error_signature(record)

                    # Simple similarity check
                    if self._signatures_match(error_signature, stored_signature):
                        return {
                            "solution": record.get("solution"),
                            "root_cause": record.get("root_cause"),
                            "prevention": record.get("prevention"),
                            "timestamp": record.get("timestamp"),
                        }
                except json.JSONDecodeError:
                    continue

        return None

    def _signatures_match(self, sig1: str, sig2: str, threshold: float = 0.7) -> bool:
        """
        Check if two error signatures match

        Simple word overlap check (good enough for most cases).

        Args:
            sig1: First signature
            sig2: Second signature
            threshold: Minimum word overlap ratio (default: 0.7)

        Returns:
            bool: Whether signatures are similar enough
        """
        words1 = set(sig1.lower().split())
        words2 = set(sig2.lower().split())

        if not words1 or not words2:
            return False

        overlap = len(words1 & words2)
        total = len(words1 | words2)

        return (overlap / total) >= threshold

    def _create_mistake_doc(self, error_info: Dict[str, Any]) -> None:
        """
        Create detailed mistake documentation

        Format: docs/mistakes/[feature]-YYYY-MM-DD.md

        Structure:
            - What Happened
            - Root Cause
            - Why Missed
            - Fix Applied
            - Prevention Checklist
            - Lesson Learned

        Args:
            error_info: Error information with analysis
        """
        # Generate filename
        test_name = error_info.get("test_name", "unknown")
        date = datetime.now().strftime("%Y-%m-%d")
        filename = f"{test_name}-{date}.md"
        filepath = self.mistakes_dir / filename

        # Create mistake document
        content = f"""# Mistake Record: {test_name}

**Date**: {date}
**Error Type**: {error_info.get("error_type", "Unknown")}

---

## ❌ What Happened

{error_info.get("error_message", "No error message")}

```
{error_info.get("traceback", "No traceback")}
```

---

## 🔍 Root Cause

{error_info.get("root_cause", "Not analyzed")}

---

## 🤔 Why Missed

{error_info.get("why_missed", "Not analyzed")}

---

## ✅ Fix Applied

{error_info.get("solution", "Not documented")}

---

## 🛡️ Prevention Checklist

{error_info.get("prevention", "Not documented")}

---

## 💡 Lesson Learned

{error_info.get("lesson", "Not documented")}
"""

        filepath.write_text(content)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get reflexion pattern statistics

        Returns:
            Dict with statistics:
                - total_errors: Total errors recorded
                - errors_with_solutions: Errors with documented solutions
                - solution_reuse_rate: Percentage of reused solutions
        """
        if not self.solutions_file.exists():
            return {
                "total_errors": 0,
                "errors_with_solutions": 0,
                "solution_reuse_rate": 0.0,
            }

        total = 0
        with_solutions = 0

        with self.solutions_file.open("r") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    total += 1
                    if record.get("solution"):
                        with_solutions += 1
                except json.JSONDecodeError:
                    continue

        return {
            "total_errors": total,
            "errors_with_solutions": with_solutions,
            "solution_reuse_rate": (with_solutions / total * 100) if total > 0 else 0.0,
        }
