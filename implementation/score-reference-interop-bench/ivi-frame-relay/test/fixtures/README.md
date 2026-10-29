# Golden fixtures of the IVI frame relay

These files are small cuts of real data. The C++ tests of the relay read them.
Each `.hex` file holds one hex string.

## Broker messages

Source: the records of the native IVI probe of the unreviewed DE4SDV
feasibility run on the bench VM of 2026-10-28 (design data, not evidence of
record). The probe subscribed through the SDV Gateway on IVI to the broker's
publication `instance1:com.android.sdv.someip.SomeIpBroker/default`, unit
`de4sdv-score-aebs-signal-frame`, with
`ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE`. For each message it recorded the
slot size (4101 bytes) and the bytes after the outer varint of the slot. It
did not record the outer varint and the rest of the slot. The tests add both
as the broker writes them: the shortest varint of the message length, and
zeros up to the slot size (`broker_translator.rs:248-279` of `some_ip`,
android17-release). So these bytes are real, and the slots that the tests
build from them are not.

The frames came from the bench's synthetic frame source, not from the frame
assembler: each frame starts with its sequence as a little-endian 64-bit
number, so they are no VisualizationFrame. The tests use them for the wrapper
and for the length prefix only.

| File | Run, record | Message | Payload | Frame | sha256 of the message |
|---|---|---|---|---|---|
| `broker_message_payload_68.hex` | T5, record 0 | 70 bytes | 68 bytes, prefix 64 | sequence 530 | `fad4fc9c6a6bc2de5e7228efb00f0a0f6db3ce9e470e4f32357792c83ab8b084` |
| `broker_message_payload_516.hex` | T5, record 1 | 519 bytes | 516 bytes, prefix 512 | sequence 531 | `5e980e36d4b2d23101c349ca252ca73d7d1670ce07eb3ff9012213c8369d5e0c` |
| `broker_message_payload_2048.hex` | T4, record 0 | 2051 bytes | 2048 bytes, prefix 2044 | sequence 82 | `2e741d5242dcd03e5023c59bb31d106050af07aecc00b2bec118b7b0687fea59` |

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
