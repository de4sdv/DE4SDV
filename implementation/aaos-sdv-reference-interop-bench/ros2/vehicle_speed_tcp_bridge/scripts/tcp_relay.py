#!/usr/bin/env python3
"""Relay the nested AAOS TCP stream to the ROS 2 VM over private TCP."""

from __future__ import annotations

import argparse
import socket
import socketserver
import threading


class RelayHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        server: RelayServer = self.server  # type: ignore[assignment]
        print(
            f"relay client={self.client_address} target={server.target_host}:{server.target_port}",
            flush=True,
        )
        try:
            target = socket.create_connection(
                (server.target_host, server.target_port),
                timeout=10,
            )
        except OSError as error:
            print(f"relay target connection failed: {error}", flush=True)
            return

        with target:
            self.request.settimeout(None)
            target.settimeout(None)
            left = threading.Thread(
                target=_pump,
                args=(self.request, target),
                daemon=True,
            )
            right = threading.Thread(
                target=_pump,
                args=(target, self.request),
                daemon=True,
            )
            left.start()
            right.start()
            left.join()
            right.join()


class RelayServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, handler, *, target_host: str, target_port: int):
        super().__init__(address, handler)
        self.target_host = target_host
        self.target_port = target_port


def _pump(source: socket.socket, destination: socket.socket) -> None:
    try:
        while True:
            data = source.recv(64 * 1024)
            if not data:
                return
            destination.sendall(data)
    except OSError:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=4711)
    parser.add_argument("--target-host", required=True)
    parser.add_argument("--target-port", type=int, default=4711)
    args = parser.parse_args()

    with RelayServer(
        (args.listen_host, args.listen_port),
        RelayHandler,
        target_host=args.target_host,
        target_port=args.target_port,
    ) as server:
        print(
            "Vehicle.Speed relay listening "
            f"{args.listen_host}:{args.listen_port} -> "
            f"{args.target_host}:{args.target_port}",
            flush=True,
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
