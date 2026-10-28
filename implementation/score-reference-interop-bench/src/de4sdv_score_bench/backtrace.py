"""Read a gdb backtrace and check the top frames of a REQ-MW-018 abort.

baselibs' aborts_upon_exception replaces ``__cxa_allocate_exception`` with a
call to ``std::abort()``. A throw anywhere in the adapter process then ends in
a core whose crashing thread shows, from the top: the frames of the signal
delivery, ``abort``, ``__cxa_allocate_exception`` of the adapter executable,
and the code that threw. gdb names a frame of the main executable without a
``from <library>`` suffix, so the override frame must have no library: a
``__cxa_allocate_exception`` of libstdc++ itself would mean the override was
not used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

_FRAME = re.compile(r"^#(?P<index>\d+)\s+(?P<rest>.*)$")
_ADDRESS = re.compile(r"^0x[0-9a-fA-F]+ in ")
_FROM = re.compile(r" from (?P<library>\S+)$")
_AT = re.compile(r" at \S+$")
_ABI_TAG = re.compile(r"\[abi:[^\]]*\]")

SIGNAL_DELIVERY_FUNCTIONS = frozenset(
    {
        "__pthread_kill_implementation",
        "__pthread_kill_internal",
        "__GI___pthread_kill",
        "__pthread_kill",
        "pthread_kill",
        "__GI_raise",
        "raise",
        "gsignal",
    }
)
ABORT_FUNCTIONS = frozenset({"abort", "__GI_abort"})
OVERRIDE_FUNCTION = "__cxa_allocate_exception"


@dataclass(frozen=True)
class Frame:
    index: int
    function: str
    library: str | None = None


@dataclass
class TopFrameCheck:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    abort_frame: Frame | None = None
    override_frame: Frame | None = None
    caller_frame: Frame | None = None


def _strip_frame_arguments(text: str) -> str:
    """Drop gdb's frame argument list, the last parenthesis group after a space."""
    if not text.endswith(")"):
        return text
    depth = 0
    for position in range(len(text) - 1, -1, -1):
        character = text[position]
        if character == ")":
            depth += 1
        elif character == "(":
            depth -= 1
            if depth == 0:
                if position > 0 and text[position - 1] == " ":
                    return text[: position - 1]
                return text
    return text


def _function_name(text: str) -> str:
    """The demangled name without its signature and ABI tags."""
    marker = "\x00"
    protected = text.replace("(anonymous namespace)", marker)
    depth = 0
    for position, character in enumerate(protected):
        if character == "<":
            depth += 1
        elif character == ">" and depth > 0:
            depth -= 1
        elif character == "(" and depth == 0:
            protected = protected[:position]
            break
    name = protected.replace(marker, "(anonymous namespace)")
    return _ABI_TAG.sub("", name).strip()


def parse_gdb_backtrace(text: str) -> list[Frame]:
    """Frames of the first backtrace in text, in order; later repeats of an index are ignored."""
    frames: list[Frame] = []
    seen: set[int] = set()
    for line in text.splitlines():
        match = _FRAME.match(line.strip())
        if match is None:
            continue
        index = int(match.group("index"))
        if index in seen:
            if index == 0 and frames:
                # gdb prints frame 0 once when it loads the core and again in
                # "bt"; a second #0 after other frames starts another backtrace.
                if len(frames) > 1:
                    break
            continue
        rest = _ADDRESS.sub("", match.group("rest"))
        library = None
        from_match = _FROM.search(rest)
        if from_match is not None:
            library = from_match.group("library")
            rest = rest[: from_match.start()]
        rest = _AT.sub("", rest)
        rest = _strip_frame_arguments(rest.strip())
        frames.append(Frame(index=index, function=_function_name(rest), library=library))
        seen.add(index)
    return frames


def check_abort_top_frames(frames: list[Frame]) -> TopFrameCheck:
    """Signal delivery, then abort, then the executable's __cxa_allocate_exception, then a caller."""
    check = TopFrameCheck(passed=False)
    if not frames:
        check.reasons.append("no frame in the backtrace")
        return check
    abort_position = next(
        (position for position, frame in enumerate(frames) if frame.function in ABORT_FUNCTIONS), None
    )
    if abort_position is None:
        check.reasons.append("no abort frame")
        return check
    check.abort_frame = frames[abort_position]
    for frame in frames[:abort_position]:
        # Without debug symbols gdb may not name the internal libc function
        # that delivers the signal; an unnamed frame there must lie in libc.
        unnamed_libc = frame.function == "??" and frame.library is not None and "/libc.so" in frame.library
        if frame.function not in SIGNAL_DELIVERY_FUNCTIONS and not unnamed_libc:
            check.reasons.append(f"frame #{frame.index} {frame.function} above abort is not signal delivery")
    if abort_position + 1 >= len(frames) or frames[abort_position + 1].function != OVERRIDE_FUNCTION:
        below = frames[abort_position + 1].function if abort_position + 1 < len(frames) else "nothing"
        check.reasons.append(f"the frame below abort is {below}, not {OVERRIDE_FUNCTION}")
        return check
    check.override_frame = frames[abort_position + 1]
    if check.override_frame.library is not None:
        check.reasons.append(
            f"{OVERRIDE_FUNCTION} comes from {check.override_frame.library}, not from the adapter executable"
        )
    if abort_position + 2 >= len(frames):
        check.reasons.append("no caller frame below the override")
    else:
        check.caller_frame = frames[abort_position + 2]
    check.passed = not check.reasons
    return check
