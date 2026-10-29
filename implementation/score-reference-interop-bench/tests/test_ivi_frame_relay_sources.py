"""Source checks of the DE4SDV IVI frame relay (ivi-frame-relay/).

CI cannot build the AOSP adapter to libsdvgatewayclient and the main of the
relay, so these checks read their sources: the adapter calls only the
functions the relay needs, subscribes with
ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE and never asks for the last
message; no source of the relay opens a connection or sends a datagram;
Android.bp builds the sources that CMake tests plus the two AOSP files; and
the init file declares a service that is not oneshot and sets no margin.
"""

from pathlib import Path
import re

RELAY = Path(__file__).resolve().parents[1] / "ivi-frame-relay"
ADAPTER = RELAY / "src" / "aosp" / "sdv_gateway_client.cpp"
MAIN = RELAY / "src" / "aosp" / "relay_main.cpp"
INIT = RELAY / "de4sdv_ivi_frame_relay.rc"

#: The C API functions of the relay: no publication, no RPC server, no discovery listener.
ALLOWED_CALLS = {
    "ASDVGateway_Client_new",
    "ASDVGateway_Client_setClientNotificationCallback",
    "ASDVGateway_Client_initComms",
    "ASDVGateway_Client_subscribeToPublicationByName",
    "ASDVGateway_Client_setNotificationCallbackForPublicationId",
    "ASDVGateway_Client_unsubscribeFromPublication",
    "ASDVGateway_Client_readAvailableMessages",
    "ASDVGateway_Client_delete",
}


def _code(path: Path) -> str:
    """The source without its comments and string literals."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    return re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', text)


def _sources() -> list[Path]:
    return sorted(path for path in RELAY.rglob("*") if path.suffix in {".cpp", ".hpp"})


def test_the_adapter_calls_only_the_functions_of_a_subscriber():
    calls = set(re.findall(r"\b(ASDVGateway_\w+)\s*\(", _code(ADAPTER)))
    assert calls == ALLOWED_CALLS


def test_the_adapter_subscribes_with_flag_none_and_never_with_the_last_message():
    code = _code(ADAPTER)
    assert re.search(r"options\.flags\s*=\s*ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE\s*;", code)
    for path in _sources():
        assert "FETCHLASTMESSAGE" not in _code(path), path.name


def test_no_source_of_the_relay_connects_or_sends_a_datagram():
    for path in _sources():
        code = _code(path)
        if path.parent.name == "test":
            continue  # the shell tests connect as the ingress does
        for call in ("connect", "sendto", "sendmsg", "publishMessages", "createPublication", "registerRpcServer"):
            assert not re.search(rf"(?<![\w.]){call}\s*\(", code), f"{path.name} calls {call}"


def test_the_loopback_server_is_fixed_at_127_0_0_1_port_4731():
    options = (RELAY / "include" / "de4sdv_ivi_frame_relay" / "options.hpp").read_text(encoding="utf-8")
    assert re.search(r"kListenAddress\s*=\s*0x7F000001\s*;", options)
    assert re.search(r"kListenPort\s*=\s*4731\s*;", options)
    shell = _code(RELAY / "src" / "shell" / "relay_shell.cpp")
    assert len(re.findall(r"::bind\s*\(", shell)) == 1
    assert "--listen" not in (RELAY / "src" / "core" / "options.cpp").read_text(encoding="utf-8")


def _bp_sources() -> list[str]:
    text = (RELAY / "Android.bp").read_text(encoding="utf-8")
    block = re.search(r"srcs:\s*\[(.*?)\]", text, flags=re.S)
    assert block
    return re.findall(r'"([^"]+)"', block.group(1))


def _cmake_library_sources() -> list[str]:
    text = (RELAY / "CMakeLists.txt").read_text(encoding="utf-8")
    sources = []
    for block in re.findall(r"add_library\(\w+ STATIC(.*?)\)", text, flags=re.S):
        sources += re.findall(r"(src/\S+\.cpp)", block)
    return sources


def test_android_bp_builds_the_tested_sources_and_the_two_aosp_files():
    tested = _cmake_library_sources()
    assert tested and all(not source.startswith("src/aosp/") for source in tested)
    assert sorted(_bp_sources()) == sorted(tested + ["src/aosp/sdv_gateway_client.cpp", "src/aosp/relay_main.cpp"])
    assert set(_bp_sources()) >= {str(path.relative_to(RELAY)) for path in (RELAY / "src" / "core").glob("*.cpp")}
    bp = (RELAY / "Android.bp").read_text(encoding="utf-8")
    assert '"libsdvgatewayclient"' in bp and 'init_rc: ["de4sdv_ivi_frame_relay.rc"]' in bp


def test_the_init_file_declares_a_restarted_service_without_a_margin_option():
    lines = [line for line in INIT.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("#")]
    services = [line for line in lines if line.startswith("service ")]
    assert services == [line for line in services if line.split()[1] == "de4sdv_ivi_frame_relay"]
    assert len(services) == 1
    assert services[0].split()[2] == "/system/bin/de4sdv_ivi_frame_relay"
    body = [line.strip() for line in lines]
    assert "oneshot" not in body
    assert "gentle_kill" in body
    assert "setprop de4sdv.aebs.frame_server.port 4731" in body
    assert not re.findall(r"--[\w-]*(?:margin|bound)[\w-]*", "\n".join(lines))
    # The options that the init file passes exist.
    options = set(re.findall(r'\{"(--[\w-]+)"', (RELAY / "src" / "core" / "options.cpp").read_text(encoding="utf-8")))
    options |= {"--log-frames", "--help"}
    assert set(re.findall(r"(--[\w-]+)", services[0])) <= options


def test_the_main_ends_a_process_whose_worker_it_left_behind():
    code = _code(MAIN)
    assert re.search(r"if\s*\(\s*!result\.worker_joined\s*\)\s*\{\s*std::_Exit\(", code)
