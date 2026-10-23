# Baseline Register

Status: controlled

| Baseline ID | ASELCM system | Scope | Version/tag | Date | Change reference | Evidence |
|---|---|---|---|---|---|---|
| BL-MW-010-P12 | System 1 + System 2 | INC-MW-010 bounded middleware V&V evidence | INC-MW-010@Phase12 | 2026-08-27 | boundedBaselineDecision010 | E-MW-011; E-MW-012; E-MW-013; E-MW-014 |

## Production releases

A production release deploys one exact `main` commit to the public SysML v2
API, viewer, and Ask viewer ([release steps](../deployment/README.md#release)).
Each one is a System 1 + System 2 baseline. The commit pins the model and the
implementation. Its `sysand-lock.toml` pins the SysML package dependencies. The
owner approval of `sysml-api-production` in the deploy run is the baseline
decision.

| Commit | Tag | Deployed | Deploy run | Privileged run | Served semantic authority |
|---|---|---|---|---|---|
| `063c4fb1f2763a366874118f3b78d9841e0d11b4` | `release-2026-10-11` | 2026-10-11 | [38127860329](https://github.com/de4sdv/DE4SDV/actions/runs/38127860329) | [38095581274](https://github.com/de4sdv/DE4SDV/actions/runs/38095581274) | `mab-32da05b896fee9d5a47874e7f305f741` (model-authority bundle; binding `sai-aebefd563fa3f1bd99aebff5a4119eae`) |
| `8c1699f81c584e77fd38e56875ca6f4ce35c865e` | `release-2026-10-15` | 2026-10-15 | [38722880517](https://github.com/de4sdv/DE4SDV/actions/runs/38722880517) | [38695759373](https://github.com/de4sdv/DE4SDV/actions/runs/38695759373) | `sai-7dc1c4830b792757ffe7d9d260fe2ef2` |
| `3cca3eaeb53aedadbf8dc929f2fb3052ef515b5e` | none | 2026-10-20 | [39252675717](https://github.com/de4sdv/DE4SDV/actions/runs/39252675717) | [39227055260](https://github.com/de4sdv/DE4SDV/actions/runs/39227055260) | `sai-feadb34ad784e7ff1409ffaf5cd1feef` |
| `21cdbfede2df90a4e8666bedc02e4b23b8b64efc` | none | 2026-10-21 | [39578322090](https://github.com/de4sdv/DE4SDV/actions/runs/39578322090) | [39542982231](https://github.com/de4sdv/DE4SDV/actions/runs/39542982231) | `sai-0bbb86166f8743f726f159040691191a` |
| `b6212d457913a4758f0d63bdbc206043d8eb65f1` | none | 2026-10-21 | [39662665485](https://github.com/de4sdv/DE4SDV/actions/runs/39662665485) | [39639315800](https://github.com/de4sdv/DE4SDV/actions/runs/39639315800) | `sai-b565a28ff2bae73230941fa090d640ad` |

For `3cca3eae` and `21cdbfed`, the deploy run shows the workflow revision
(`32e904ea`, `28fa4e8d`). The deploy job log (`DEPLOY_SHA`) names the deployed
commit. Five earlier deploys, from 2026-09-02 to 2026-10-08, are not recorded.
Run artifacts and logs expire after the retention period. The run records stay.
