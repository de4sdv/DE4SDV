# Golden fixtures of the SOME/IP receiver

These files are small cuts of real data. The C++ tests of the receiver core
and the Python tests of the bench evaluators read them. Each `.hex` file holds
one hex string.

## SOME/IP and SOME/IP-SD messages

Source: the guest-side captures (`guest_wire.pcap`) of GitHub Actions run
40532187964 of the DE4SDV gateway spike, the job at `inc_someip_gateway`
`723119c4`. That commit has the sources of `d9eac670` except the baselibs
version. In those captures, someipd uses vsomeip 3.6.1 on 10.250.0.1, and a
vsomeip 3.7.6 client (`4187431d`) runs on 10.250.0.2. The packet index counts
the IPv4 TCP and UDP packets of the capture from 0.

| File | Scenario | Packet | What |
|---|---|---|---|
| `sd_offer_multicast.hex` | s17-gateway-pair-restart | 0 | OfferService of someipd, session 1, reboot flag, TCP endpoint 10.250.0.1:30509 |
| `sd_subscribe_from_vsomeip_client.hex` | s17-gateway-pair-restart | 4 | SubscribeEventgroup of the client, TTL 3, TCP endpoint 10.250.0.2:35005 |
| `sd_subscribe_ack.hex` | s17-gateway-pair-restart | 5 | SubscribeEventgroupAck, TTL 3 |
| `sd_offer_before_restart_last.hex` | s17-gateway-pair-restart | 125 | the last OfferService before the restart, session 7 |
| `sd_subscribe_nack_offer_pending.hex` | s17-gateway-pair-restart | 162 | Nack of the restarted someipd (TTL 0, session 1): the service was not offered yet |
| `sd_stop_subscribe_from_vsomeip_client.hex` | s17-gateway-pair-restart | 164 | StopSubscribeEventgroup of the client after the Nack |
| `sd_offer_after_someipd_restart.hex` | s17-gateway-pair-restart | 165 | the first OfferService of the restarted someipd, session 1 |
| `sd_stop_offer.hex` | s07-host-stop-sequence | 176 | StopOffer when someipd stops |
| `sd_find_service_from_vsomeip_client.hex` | s07-host-stop-sequence | 1 | FindService of the client |
| `sd_offer_unicast.hex` | s02-late-subscriber | 6 | unicast OfferService, the answer to a FindService |
| `sd_stop_subscribe_and_subscribe_from_vsomeip_client.hex` | s09-stalled-guest | 369 | two entries in one message that share one endpoint option |
| `tcp_notifications_someipd.hex` | s17-gateway-pair-restart | 19, 21, 23, 25 | the first four notifications of the TCP stream 10.250.0.1:30509 to 10.250.0.2:35005, as one byte stream |

The notification payloads come from the spike's publisher. Their prefix is
big-endian, so the receiver drops them as `length_prefix_mismatch`: the tests
use this as a negative case.

`someip_guest_wire_pair_restart.pcap` holds packets 0 to 11, 19 to 24, 132 to
135, 158 to 170 and 188 to 197 of the same s17 capture, with the original pcap
header and records (13342 bytes, sha256
`03aecfe39b58dca663f84f5149b02012a9c0ef82c421144c525eee167bfb5577`). The cut
keeps the first subscription, the first notifications, the end of the first
TCP connection, the Nack, the new offer, the new subscription and the frames
that the restarted pair sent from the samples it had stored.

## VisualizationFrame encodings

The protobuf runtime for Python (`google.protobuf` 3.12.4) encoded the four
`visualization_frame_*.hex` frames. The message descriptor was built field for
field from `interface/aebs_visualization.proto` of the visualization bench
(`implementation/aebs-aaos-sdv-visualization-bench`).

| File | sequence | frame_timestamp_ns | Other fields |
|---|---|---|---|
| `visualization_frame_minimal.hex` | 42 | 1793116443934013818 | schema 1.1, bridge receipt time, source identity |
| `visualization_frame_full.hex` | 1234567 | 1793116449339467540 | every field, 24 target points |
| `visualization_frame_large_sequence_negative_timestamp.hex` | 2^63 + 5 | -1 | schema 1.1, source identity |
| `visualization_frame_default_sequence_and_timestamp.hex` | 0 (absent) | 0 (absent) | schema 1.1, source identity |
