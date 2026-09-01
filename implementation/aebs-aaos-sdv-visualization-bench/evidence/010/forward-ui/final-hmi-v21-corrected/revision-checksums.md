# Correction-deployed revision checksums (INC-AEBS-010 final campaign, 2026-09-01)

The evidence in final-hmi-v21-corrected was captured from the exact corrected
working-tree revision (HEAD 4d8dc1b4cb9ce984e31db74ac25165816c91eab6 plus the
uncommitted semantic-HMI correction, 17 dirty files at capture time).

sha256 prefixes of the deployed corrected sources:

- a366df84cb1be1d6  MainActivity.java
- 42811c65bce4932e  ForwardSituationView.java
- d6af0fc36f0c2462  SituationRenderModel.java
- c84736fcc0b92f98  activity_main.xml
- 454bae33f2e225e3  source_adapter.py
- 50cd098141cb33a6  ingress/main.cpp

Provenance method: AOSP modules De4sdvAebsVisualizationApp and
de4sdv_aebs_ingress were rebuilt on the bench from the corrected overlay
staged from this worktree, then installed on a freshly created AAOS guest.
Guest UI dumps and the state stills were visually and textually checked for
absence of the removed distance pair before recording. The pre-recording
monitoring screenshot is final-corrected-monitoring.png in the campaign
bundle (sha256 6fe8bd1fa15d3b4ac84a4779785c0cd319f738bf45cd961b7020dc7fafe51c2c).
