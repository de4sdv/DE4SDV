# Option A, kept as the first fallback (rejected as the design)

This directory is the **previous revision** of the observation path, unchanged. It
was designed first, recommended, and rejected in the S1–S5 review: the
recommendation rested on a false premise
(the S-CORE publisher was described as a foreign slice that already runs, when it is
this slice's own uncompiled code), and MAP-DRIVING-OPERATIONAL-STATE states that the
interop maps the three events onto **one typed VSIDL message**
`DrivingOperationalState`. Option B — the current design — is that.

## What it is

```
S-CORE publisher: protobuf wire format of de4sdv.driving.v1.DrivingOperationalState
  → SOME/IP event payload: those bytes, unchanged
  → SDV Core broker: message_translation_mode INTERPRET_AS_BYTES
  → Data Tunnel topic: com.android.sdv.someip.De4sdvDrivingOperationalStateFrame
                       { bytes data = 1; variable_type_max_size = 2048 }
  → IVI app: SlotFramer locates the message in the delivered bytes, the generated
             parser decodes it, the record is built from the parsed message
```

The broker fact behind it is true and still stands: a protobuf payload can cross the
broker only as bytes, because REFLECTION translates a SOME/IP *struct*, and no
`type_definition` turns protobuf tags into fields.

## Why it is not the design

The topic's type would be a carrier, not the ICD's message. The model says the topic
is `DrivingOperationalState`; a bytes carrier makes that sentence false. Fixing it
on paper is a **model amendment**, which is the owner's decision — not something an
implementer may do because the code was easier.

## What would have to change to take it

1. **Model amendment** to MAP-DRIVING-OPERATIONAL-STATE (and the ICD's §3 sentence):
   the topic type is a bytes carrier; the typed message is decoded at the observer.
2. **Owner decision**, recorded with the reason (a broker limit, or a gate failure
   in option B).
3. Then: restore the files below into their old places, restore the app's
   `SlotFramer` + `OperationalDataDecoder` path, and rebuild the core image with the
   carrier proto and the `INTERPRET_AS_BYTES` mapping. The old
   `tests/test_contract_and_framing.py` is here too.

Cost, from the previous estimate: about 4 h on the VM (the core build is the same
1.5 h; the app and its slot framing were already written and tested locally), plus
the paperwork.

## What is here

| Path | Old role |
|---|---|
| `contract/de4sdv_driving_operational_state_frame.proto` | the catalog carrier type (`bytes data = 1`, 2048) |
| `contract/observed/de4sdv_driving_operational_state.proto` | the protobuf payload schema the S-CORE side serialized (doubles for times) |
| `interop/de4sdv_driving_operational_state.vsidl` | the `INTERPRET_AS_BYTES` mapping, three events to one topic |
| `interop/de4sdv_driving_operational_state_bundle.vsidl` | the broker's publisher declaration for the carrier |
| `interop/broker_acl_append.textproto` | the broker publish ACL for the carrier message |
| `interop/acl/*.textproto` | the ACL pair naming the carrier message |
| `app/proto/…frame.proto` | the app's annotation-free copy of the carrier |
| `app/src/.../SlotFramer.java` | locates the ICD message inside the delivered bytes, names the layout |
| `app/src/.../OperationalStateDecoder.java` | parses the payload, builds the record, prints the logcat line |
| `app/tests/.../SlotFramerTest.java` | the framer's JVM test |
| `tests/test_contract_and_framing.py` | the old local contract test (28-field schema, carrier bound, slot layouts) |

**These files are exactly as they were.** Their comments reference the old layout
(`../observed/`, `app/proto`, `GatewayStateSubscriber.java`, the 28-field table) and
were not edited, because a fallback is only useful if what it preserves is what was
reviewed. Read them as a historical record; the `check` steps of the current scripts
no longer look at this directory, and `stage_ivi_observer.sh check` actively fails if
a `bytes data` type reappears in `app/`.
