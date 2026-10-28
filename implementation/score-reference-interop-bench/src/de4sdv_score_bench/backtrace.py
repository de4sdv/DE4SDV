"""Read a gdb backtrace and check the top frames of a REQ-MW-018 abort.

baselibs' aborts_upon_exception replaces ``__cxa_allocate_exception`` with a
call to ``std::abort()``. A throw anywhere in the adapter process then ends in
a core whose crashing thread shows, from the top: the frames of the signal
delivery, ``abort``, ``__cxa_allocate_exception`` of the adapter executable,
and the code that threw.

Where a frame's code lies is decided by its address, not by the text form of
the gdb line: gdb's ``info proc mappings`` of the core gives the address
range of each mapped file, and the frame's address picks the file. gdb
prints ``from <library>`` only for a frame without debug information, and
``at <file>:<line>`` for one with it, so the text alone cannot tell a
libstdc++ frame with debug information from a frame of the executable. An
inlined frame has no address of its own; it lies in the code of the frame
above it. The check fails when gdb names a library that the address does
not confirm, and when the allocation frame comes from libstdc++'s own source.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import re

_FRAME = re.compile(r"^#(?P<index>\d+)\s+(?P<rest>.*)$")
_ADDRESS = re.compile(r"^(?P<pc>0x[0-9a-fA-F]+) in ")
_FROM = re.compile(r" from (?P<library>\S+)$")
_AT = re.compile(r" at (?P<source>\S+)$")
# The source of libstdc++'s own exception allocation and throw helpers.
_LIBSTDCXX_SOURCE = re.compile(r"(^|/)(libsupc\+\+|libstdc\+\+-v3)/")
_ABI_TAG = re.compile(r"\[abi:[^\]]*\]")
_MAPPING = re.compile(
    r"^\s*(?P<start>0x[0-9a-fA-F]+)\s+(?P<end>0x[0-9a-fA-F]+)\s+(?P<size>0x[0-9a-fA-F]+)\s+"
    r"(?P<offset>0x[0-9a-fA-F]+)\s+(?:[rwxsp-]{4}\s+)?(?P<objfile>/\S.*?)\s*$"
)

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
    # The library that gdb names after "from"; None when gdb names none.
    library: str | None = None
    # The frame's address; an inlined frame takes the address of the frame above it.
    pc: int | None = None
    # The mapped file that holds pc, from the core's mappings; None when unknown.
    objfile: str | None = None
    # The source file that gdb names after "at"; None when gdb names none.
    source: str | None = None


@dataclass(frozen=True)
class Mapping:
    start: int
    end: int
    offset: int
    objfile: str


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
        rest = match.group("rest")
        pc = None
        address = _ADDRESS.match(rest)
        if address is not None:
            pc = int(address.group("pc"), 16)
            rest = rest[address.end() :]
        elif frames:
            pc = frames[-1].pc  # an inlined frame: the code of the frame above
        library = None
        from_match = _FROM.search(rest)
        if from_match is not None:
            library = from_match.group("library")
            rest = rest[: from_match.start()]
        source = None
        at_match = _AT.search(rest)
        if at_match is not None:
            source = at_match.group("source").rsplit(":", 1)[0]
            rest = rest[: at_match.start()]
        rest = _strip_frame_arguments(rest.strip())
        frames.append(Frame(index=index, function=_function_name(rest), library=library, pc=pc, source=source))
        seen.add(index)
    return frames


def parse_gdb_mappings(text: str) -> list[Mapping]:
    """The file mappings of gdb's ``info proc mappings`` output for a core."""
    mappings = []
    for line in text.splitlines():
        match = _MAPPING.match(line)
        if match is None:
            continue
        mappings.append(
            Mapping(
                start=int(match.group("start"), 16),
                end=int(match.group("end"), 16),
                offset=int(match.group("offset"), 16),
                objfile=match.group("objfile"),
            )
        )
    return mappings


def locate_frames(frames: list[Frame], mappings: list[Mapping]) -> list[Frame]:
    """The frames with the mapped file that holds each address."""
    located = []
    for frame in frames:
        objfile = None
        if frame.pc is not None:
            objfile = next(
                (mapping.objfile for mapping in mappings if mapping.start <= frame.pc < mapping.end), None
            )
        located.append(replace(frame, objfile=objfile))
    return located


def read_located_frames(backtrace_text: str, mappings_text: str) -> list[Frame]:
    return locate_frames(parse_gdb_backtrace(backtrace_text), parse_gdb_mappings(mappings_text))


def object_name(path: str) -> str:
    """The file name of path up to and with ``.so``, so a link and its target compare equal."""
    name = path.rsplit("/", 1)[-1]
    position = name.find(".so")
    return name[: position + 3] if position >= 0 else name


def same_object(first: str, second: str) -> bool:
    return object_name(first) == object_name(second)


def lies_in(frame: Frame, name: str) -> bool:
    """True when the frame's address lies in a file whose object name is that of name."""
    return frame.objfile is not None and object_name(frame.objfile) == object_name(name)


def _origin_reasons(frame: Frame, label: str) -> list[str]:
    if frame.pc is None:
        return [f"{label} #{frame.index} {frame.function} has no address"]
    if frame.objfile is None:
        return [f"{label} #{frame.index} {frame.function} lies in no mapped file"]
    if frame.library is not None and not same_object(frame.library, frame.objfile):
        return [f"{label} #{frame.index}: gdb names {frame.library}, the address lies in {frame.objfile}"]
    return []


def check_abort_top_frames(frames: list[Frame], executable: str) -> TopFrameCheck:
    """Signal delivery, then abort, then the override in the executable, then a caller.

    frames must be located (locate_frames); executable is the file name of
    the adapter executable.
    """
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
        if frame.function in SIGNAL_DELIVERY_FUNCTIONS:
            continue
        if frame.function == "??" and lies_in(frame, "libc.so"):
            continue
        check.reasons.append(f"frame #{frame.index} {frame.function} above abort is not signal delivery")
    if abort_position + 1 >= len(frames) or frames[abort_position + 1].function != OVERRIDE_FUNCTION:
        below = frames[abort_position + 1].function if abort_position + 1 < len(frames) else "nothing"
        check.reasons.append(f"the frame below abort is {below}, not {OVERRIDE_FUNCTION}")
        return check
    check.override_frame = frames[abort_position + 1]
    origin = _origin_reasons(check.override_frame, "the override frame")
    if origin:
        check.reasons.extend(origin)
    elif not lies_in(check.override_frame, executable):
        check.reasons.append(
            f"{OVERRIDE_FUNCTION} lies in {check.override_frame.objfile}, not in the executable {executable}"
        )
    if check.override_frame.source is not None and _LIBSTDCXX_SOURCE.search(check.override_frame.source):
        check.reasons.append(
            f"{OVERRIDE_FUNCTION} comes from the libstdc++ source {check.override_frame.source}, not from the override"
        )
    if abort_position + 2 >= len(frames):
        check.reasons.append("no caller frame below the override")
    else:
        check.caller_frame = frames[abort_position + 2]
        check.reasons.extend(_origin_reasons(check.caller_frame, "the caller frame"))
    check.passed = not check.reasons
    return check


def frame_text(frame: Frame) -> str:
    """One frame for a report: the function and the file that holds its address."""
    function = "abort" if frame.function in ABORT_FUNCTIONS else frame.function
    if frame.objfile is None:
        return f"{function} (address in no mapped file)" if frame.pc is not None else f"{function} (no address)"
    return f"{function} in {frame.objfile}"


def first_named_frame_below_override(frames: list[Frame], check: TopFrameCheck) -> Frame | None:
    """The first frame with a name from the caller down, to report where a library threw."""
    if check.caller_frame is None:
        return None
    below = frames[frames.index(check.caller_frame) :]
    return next((frame for frame in below if frame.function != "??"), None)
