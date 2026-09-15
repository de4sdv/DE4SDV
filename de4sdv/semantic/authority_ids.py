"""Authority-path identifiers shared by the runtime surfaces.

The identifier is provenance/cache metadata only: it labels WHICH authority
path produced an answer. It never changes query semantics.
"""

from __future__ import annotations

#: Deterministic identifier of the legacy authored ``KernelContract`` path
#: (production default; unchanged behavior).
LEGACY_AUTHORITY_ID = "de4sdv.o0-o1-authored-v1"
