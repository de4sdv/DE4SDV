# S1 media disposition

No recording of the judged session S1 is in Git, and none is published. Each
recording and archive of the fetched session tree is listed with its path in
the tree, its SHA-256, its byte count, its disposition and its availability
in [`external-media.json`](external-media.json), which
`tools/refresh_driver_assistance_s1_evidence.py` writes from the tree.

| Kind | Where in the session tree | Disposition | Availability |
|---|---|---|---|
| Chase view of each run, on the simulator host | `sim/out/rec_<run>/chase_view.mp4` | `observed_bounded` | maintainer archive; all 16 are fetched, each with the SHA-256 that the simulator host gave (`sim/fetch_chase/fetch_chase.json`) |
| Capture of the IVI guest's display in each run | `guest/out/capture_<run>/seg_<n>.mp4` | `observed_bounded` | maintainer archive |
| Screen captures of the guests' displays at the start and the end of each capture | `guest/out/capture_<run>/screencap_*.png` | `observed_bounded` | maintainer archive |
| The candidate's own visualization of each run, drawn by the DE4SDV visualization recorder | `score/out/score_<run>/score_side/visualization/visualization.mkv` | `observed_bounded` | maintainer archive; all 16 are fetched, each with the SHA-256 that the S-CORE host gave (`score/fetch_visualization/fetch_visualization.json`) |
| The candidate's data log of each run | named by `rawObservationArtifact` of its record, kept on the S-CORE host | `observed_bounded` | named by path and SHA-256 only |
| Archives of each host's output and of the bench kit | `*.tgz` | `observed_bounded` | maintainer archive |

## Hard boundary

- No case reads a recording. Every case reads the machine records of
  `records.json`; a recording shows a run, and the verdict rests on the
  records.
- No publication cut exists. A cut, a title card or any edit is made only on
  the owner's word, after the results are shown to the VisionPilot
  maintainers, and it is never evidence of a run.
- A maintainer archive is not public evidence. Where a record names a file on
  the S-CORE host by its path there, its SHA-256 is its identity.
- Every chase view and every visualization recording of the session tree is
  fetched, 16 of each (`external-media.json` lists them), and the
  `benchRecordingArtifact` of each run record names its chase view and its
  visualization recording by SHA-256.
