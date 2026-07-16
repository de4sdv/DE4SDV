# Shared Assets

This directory is a **reference**, not a storage location.

The actual shared asset superset (150% model) lives in the textual notation area:

```
textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml
```

That SysML v2 model contains the native `variation`/`variant` constructs that
define the structural variation points. Feature selections from
[`../feature-configurations/`](../feature-configurations/) resolve against
those variation points to produce configured member products in
[`../product-models/`](../product-models/).
