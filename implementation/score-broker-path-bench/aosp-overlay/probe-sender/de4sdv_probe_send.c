/*
 * de4sdv_probe_send: one bound datagram or one timed TCP connect, then exit.
 *
 * The REQ-MW-016 isolation probe (host_isolation_probe.sh) and the spoofed
 * SOME/IP SD offer (send_sd_offer.sh) need a sender that pins the egress
 * device, the source address and the source port, so a probe really leaves on
 * its named interface (review R41) and an SD offer really comes from the SD
 * source port (review R43). toybox nc does neither, and it loops on a UDP
 * socket after stdin EOF (reviews R39, R40). This tool does exactly one send
 * or one connect and exits; it never waits for a reply and never loops.
 *
 *   de4sdv_probe_send --device DEV --source ADDR --sport N --host ADDR --port N
 *                     [--tcp] [--timeout-ms N] [--file PATH]
 *
 * UDP (the default): bind the device, the source address and the source port,
 * then send one datagram (payload from stdin, or --file) to host:port.
 * TCP (--tcp): the same binding, then one connect with a timeout; a payload,
 * if any, is sent after the connect. --sport 0 lets the kernel choose the
 * source port (for the :4721 connect, where an ephemeral port is fine).
 *
 * Exit code: 0 on a successful send or connect; otherwise the errno of the
 * failing call (so a refused connect is 111, a timeout 110, a bad source
 * address 99). Diagnostics go to stderr; nothing is written to stdout.
 *
 * POSIX C11, no dependencies. It runs on the AAOS guest (built in the AOSP
 * tree by the Android.bp beside it). CI compiles it with the host compiler;
 * the six namespace tests skip there. Local tests and the off-VM harness
 * exercise it in unprivileged user and network namespaces.
 */

/* SO_BINDTODEVICE is a GNU extension on glibc, so the host compile asks for it
 * with _GNU_SOURCE; bionic (the AOSP build) defines it unconditionally. */
#define _GNU_SOURCE

#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <netinet/in.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

enum { MAX_PAYLOAD = 65507 }; /* the largest UDP payload over IPv4 */

static int fail(const char *what) {
    int code = errno ? errno : 1;
    fprintf(stderr, "de4sdv_probe_send: %s: %s\n", what, strerror(code));
    return code & 0xff ? code & 0xff : 1;
}

static int read_payload(const char *path, unsigned char *buf, size_t cap, size_t *out_len) {
    FILE *in = stdin;
    if (path) {
        in = fopen(path, "rb");
        if (!in) {
            return -1;
        }
    }
    size_t total = 0;
    size_t n;
    while (total < cap && (n = fread(buf + total, 1, cap - total, in)) > 0) {
        total += n;
    }
    int read_error = ferror(in);
    if (path) {
        fclose(in);
    }
    if (read_error) {
        return -1;
    }
    *out_len = total;
    return 0;
}

int main(int argc, char **argv) {
    const char *device = NULL, *source = NULL, *host = NULL, *file = NULL;
    long sport = -1, dport = -1, timeout_ms = 1000;
    int use_tcp = 0;

    static struct option options[] = {
        {"tcp", no_argument, NULL, 't'},
        {"device", required_argument, NULL, 'd'},
        {"source", required_argument, NULL, 's'},
        {"sport", required_argument, NULL, 'q'},
        {"host", required_argument, NULL, 'h'},
        {"port", required_argument, NULL, 'p'},
        {"timeout-ms", required_argument, NULL, 'w'},
        {"file", required_argument, NULL, 'f'},
        {NULL, 0, NULL, 0},
    };
    int opt;
    while ((opt = getopt_long(argc, argv, "td:s:q:h:p:w:f:", options, NULL)) != -1) {
        switch (opt) {
        case 't': use_tcp = 1; break;
        case 'd': device = optarg; break;
        case 's': source = optarg; break;
        case 'q': sport = strtol(optarg, NULL, 10); break;
        case 'h': host = optarg; break;
        case 'p': dport = strtol(optarg, NULL, 10); break;
        case 'w': timeout_ms = strtol(optarg, NULL, 10); break;
        case 'f': file = optarg; break;
        default:
            fprintf(stderr, "usage: %s --device DEV --source ADDR --sport N "
                            "--host ADDR --port N [--tcp] [--timeout-ms N] [--file PATH]\n",
                    argv[0]);
            return 2;
        }
    }
    if (!device || !source || !host || sport < 0 || dport < 0 || dport > 65535 || sport > 65535) {
        fprintf(stderr, "de4sdv_probe_send: device, source, sport, host and port are required\n");
        return 2;
    }

    struct sockaddr_in src = {0}, dst = {0};
    src.sin_family = dst.sin_family = AF_INET;
    src.sin_port = htons((unsigned short)sport);
    dst.sin_port = htons((unsigned short)dport);
    if (inet_pton(AF_INET, source, &src.sin_addr) != 1) {
        fprintf(stderr, "de4sdv_probe_send: bad source address %s\n", source);
        return 2;
    }
    if (inet_pton(AF_INET, host, &dst.sin_addr) != 1) {
        fprintf(stderr, "de4sdv_probe_send: bad host address %s\n", host);
        return 2;
    }

    int fd = socket(AF_INET, use_tcp ? SOCK_STREAM : SOCK_DGRAM, 0);
    if (fd < 0) {
        return fail("socket");
    }

    /* Pin the egress device: the datagram leaves on this interface whatever
     * the route says (review R41). SO_BINDTODEVICE takes the interface name. */
    if (setsockopt(fd, SOL_SOCKET, SO_BINDTODEVICE, device, (socklen_t)(strlen(device) + 1)) < 0) {
        int code = fail("SO_BINDTODEVICE");
        close(fd);
        return code;
    }
    int one = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
#ifdef SO_REUSEPORT
    setsockopt(fd, SOL_SOCKET, SO_REUSEPORT, &one, sizeof one);
#endif

    /* Bind the source address, and the source port when one was asked for
     * (sport 0 lets the kernel choose it, for the :4721 connect). */
    if (bind(fd, (struct sockaddr *)&src, sizeof src) < 0) {
        int code = fail("bind source");
        close(fd);
        return code;
    }

    unsigned char payload[MAX_PAYLOAD];
    size_t payload_len = 0;
    int want_payload = !use_tcp || file != NULL;
    if (want_payload && read_payload(file, payload, sizeof payload, &payload_len) < 0) {
        int code = fail("read payload");
        close(fd);
        return code;
    }

    if (!use_tcp) {
        ssize_t sent = sendto(fd, payload, payload_len, 0, (struct sockaddr *)&dst, sizeof dst);
        if (sent < 0) {
            int code = fail("sendto");
            close(fd);
            return code;
        }
        close(fd);
        return 0;
    }

    /* TCP: one connect with a timeout, so it never hangs (review R40). */
    int flags = fcntl(fd, F_GETFL, 0);
    fcntl(fd, F_SETFL, flags | O_NONBLOCK);
    int rc = connect(fd, (struct sockaddr *)&dst, sizeof dst);
    if (rc < 0 && errno == EINPROGRESS) {
        struct pollfd pfd = {.fd = fd, .events = POLLOUT};
        int ready = poll(&pfd, 1, (int)timeout_ms);
        if (ready == 0) {
            errno = ETIMEDOUT;
            int code = fail("connect");
            close(fd);
            return code;
        }
        if (ready < 0) {
            int code = fail("poll");
            close(fd);
            return code;
        }
        int err = 0;
        socklen_t len = sizeof err;
        getsockopt(fd, SOL_SOCKET, SO_ERROR, &err, &len);
        if (err != 0) {
            errno = err;
            int code = fail("connect");
            close(fd);
            return code;
        }
    } else if (rc < 0) {
        int code = fail("connect");
        close(fd);
        return code;
    }
    if (payload_len > 0) {
        ssize_t sent = send(fd, payload, payload_len, 0);
        if (sent < 0) {
            int code = fail("send");
            close(fd);
            return code;
        }
    }
    close(fd);
    return 0;
}
