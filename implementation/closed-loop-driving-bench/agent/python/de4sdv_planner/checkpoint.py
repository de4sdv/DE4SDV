"""The checkpoint engine of de4sdv_planner: the R2 stack of the closed-loop readiness probes, ported
from the CL harness (p3cl_planner.py) without changing its math:
  - the runtime patches installed in the harness's order, cuDNN asserted;
  - the pinned checkpoint loaded by the pinned source (pipelines.inference.load_policy);
  - warm-up and parity on the recorded upstream sample against the fp32 reference;
  - one persistent no_grad + bf16 autocast region, thread-local: setup runs before FEO starts, and
    bind_thread() enters the region on FEO worker 40, the thread of every later call;
  - ImageNet-normalised tiles resized on the GPU (antialiased bilinear), the native 1024 front tile
    with the base front tile derived from it; five StatefulCameraFPNCache streams, one per 100 ms
    phase; capture timestamps from the frame index;
  - history projections from the REF poses; the ego-motion history with yaw rate and curvature
    given as 0 (REQ-DRIVING-008 as amended, history.py);
  - map_context / route_mask from the agent's rasterizer (S3, bit-exact with upstream) at the step's
    REF pose, or the camera-only context when absent.
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

from . import history as H
from . import rig as R

PATCHES_R2 = ["p2h_dynamo_cfg:cfg",
              "p2h_rev:front+tcast+clm+clp+clv+kern+pos+gemm+ctf+cbb+cpl+tsap+relu+hpack+lnf+tsm+ssm+tsv",
              "p2h_layer0c:layer0", "p2h_compile4:compile", "p2h_nochunk:big"]


class CheckpointEngine:
    name = "checkpoint"

    def __init__(self, cfg: dict):
        t_setup = time.monotonic()
        os.environ.update({"P2HR_SCA_CFG": "8,1,2", "P2HR_TSA_CFG": "4,1,2", "P2HR_MIN_ROWS": "40000",
                           "P2HR_PACK_MAX": str(cfg.get("pack_max", 64))})
        p2 = cfg.get("p2_root", "/opt/de4sdv-p2")
        src = p2 + "/src"
        for p in [p2 + "/p2h", p2 + "/p2g", src + "/Platform", src + "/Model"][::-1]:
            if p not in sys.path:
                sys.path.insert(0, p)
        import torch
        import torch.nn.functional as F
        self.torch, self.F = torch, F
        cudnn = torch.backends.cudnn.version()
        if cfg.get("cudnn") is not None and cudnn != int(cfg["cudnn"]):
            raise RuntimeError("cuDNN %s, configuration names %s" % (cudnn, cfg["cudnn"]))
        self.patches = list(cfg.get("patches", PATCHES_R2))
        self.mods = {}
        for spec in self.patches:
            mod, mode = spec.split(":")
            self.mods[mod] = __import__(mod)
            self.mods[mod].install(mode)
        import pipelines.inference as pinf
        from model_components.view_fusion.projection import PinholeProjection
        from training.dataset_policy import adapt_egomotion_history, training_policy_for_dataset
        from training.losses.control_rollout import integrate_controls_torch
        self.PinholeProjection = PinholeProjection
        self.adapt = adapt_egomotion_history
        self.integrate = integrate_controls_torch
        dev = self.dev = "cuda"
        z = np.load(cfg["input_sample"])
        TPL = self.TPL = {k: torch.from_numpy(z[k]).to(dev) for k in z.files}
        self.model = model = pinf.load_policy(Path(cfg["checkpoint_path"]), dev)[0]
        self.vhb = getattr(model, "visual_history_buffer", None) is not None
        self.noise = torch.zeros(1, 128, device=dev)
        self.cam_only = {k: torch.zeros_like(TPL[k]) for k in
                         ("map_context", "route_mask", "visual_history", "map_valid", "route_valid")}
        sample_ctx = {k: TPL[k] for k in self.cam_only}
        self.nav_on = torch.ones_like(TPL["map_valid"])
        self.avail = torch.ones(1, dtype=torch.bool, device=dev)
        import p2h_graph
        p2h_graph.make_capture_safe(self.avail)
        self.mean = torch.tensor([0.485, 0.456, 0.406], device=dev).view(1, 3, 1, 1)
        self.std = torch.tensor([0.229, 0.224, 0.225], device=dev).view(1, 3, 1, 1)
        payload, self.cams = R.load_profile(cfg["profile"])
        self.policy = training_policy_for_dataset(payload["dataset_name"])
        self.curv = R.egomotion_rule(payload)

        # warm-up and parity on the recorded sample (as the harness)
        F_ = F
        wproj = PinholeProjection(TPL["camera_projection_matrix"], geometry_type="pinhole")
        whist = tuple(PinholeProjection(TPL["camera_history_projection_matrix"][:, i], geometry_type="pinhole")
                      for i in range(7))
        wfproj = PinholeProjection(TPL["front_camera_projection_matrix"], geometry_type="pinhole")
        wfpn = F_.interpolate(TPL["front_camera_tile"], size=(512, 512), mode="bilinear", antialias=True)
        wargs = (TPL["camera_tiles"], TPL["front_camera_tile"], wfpn, wproj, wfproj, TPL["camera_history_tiles"],
                 whist, TPL["egomotion_history"])

        def timed(n, ctx, cache, stream, t0):
            lat = []
            for i in range(n):
                torch.cuda.synchronize()
                t = time.perf_counter()
                self._call(*wargs, cache, stream, t0 + 500_000 * i, ctx=ctx).float().cpu()
                lat.append((time.perf_counter() - t) * 1000)
            return lat

        cache_s = model.create_stateful_camera_fpn_cache()
        first = self._call(*wargs, cache_s, "sample", 4_000_000, ctx=sample_ctx).float().cpu().numpy().reshape(-1)
        ref32 = np.load(cfg["fp32_reference"]).reshape(-1)
        parity = {"max_abs": float(np.abs(first - ref32).max()), "mean_abs": float(np.abs(first - ref32).mean())}
        timed(9, sample_ctx, cache_s, "sample", 4_500_000)
        cache_c = model.create_stateful_camera_fpn_cache()
        timed(10, self.cam_only, cache_c, "camonly", 4_000_000)
        self._timed, self._sample_ctx = timed, sample_ctx
        self.outer = contextlib.ExitStack()
        self.outer.enter_context(torch.no_grad())
        self.outer.enter_context(torch.autocast("cuda", dtype=torch.bfloat16))
        timed(3, sample_ctx, cache_s, "sample", 16_500_000)
        timed(3, self.cam_only, cache_c, "camonly", 16_500_000)
        idle = timed(15, sample_ctx, cache_s, "sample", 18_000_000)
        idle_c = timed(15, self.cam_only, cache_c, "camonly", 18_000_000)
        del cache_s, cache_c
        self.caches = [model.create_stateful_camera_fpn_cache() for _ in range(5)]
        self.tiles, self.fronts, self.nav, self.rows = {}, {}, {}, {}
        self.poses = H.PoseRing()
        self.counts = {"gap_reset": 0, "reprime": 0}
        self.origin = None
        self.record = {"engine": self.name, "cudnn": int(cudnn), "torch": torch.__version__,
                       "device": torch.cuda.get_device_name(0), "patches": self.patches,
                       "parity": dict(parity, reference="fp32 on the recorded upstream sample"),
                       "warmupSteps": 1 + 9 + 10 + 3 + 3 + 15 + 15, "idlePlanMsMedian": float(np.median(idle)),
                       "idlePlanMsMedianCameraOnly": float(np.median(idle_c)),
                       "visualHistoryBuffer": self.vhb, "setupSeconds": round(time.monotonic() - t_setup, 1)}

    def bind_thread(self) -> dict:
        """Bind the engine to the calling thread (inferPlan's startup on FEO worker 40): enter the
        persistent no_grad + bf16 autocast region there, and absorb the thread's first-use costs
        (cuBLAS and cuDNN handles) with three timed calls per context on fresh caches."""
        import threading
        torch = self.torch
        t0 = time.monotonic()
        self.outer_bound = contextlib.ExitStack()
        self.outer_bound.enter_context(torch.no_grad())
        self.outer_bound.enter_context(torch.autocast("cuda", dtype=torch.bfloat16))
        cache_s = self.model.create_stateful_camera_fpn_cache()
        cache_c = self.model.create_stateful_camera_fpn_cache()
        lat_s = self._timed(3, self._sample_ctx, cache_s, "sample", 30_000_000)
        lat_c = self._timed(3, self.cam_only, cache_c, "camonly", 30_000_000)
        del cache_s, cache_c
        rec = {"thread": threading.get_ident(), "bindPlanMs": [round(x, 2) for x in lat_s],
               "bindPlanMsCameraOnly": [round(x, 2) for x in lat_c], "bindSeconds": round(time.monotonic() - t0, 3)}
        self.record["bind"] = rec
        return rec

    def _call(self, tiles, front, front_fpn, proj, fproj, hist_tiles, hist_proj, ego_hist, cache, stream, t_us,
              ctx=None):
        ctx = ctx if ctx is not None else self.cam_only
        torch = self.torch
        if self.vhb:
            self.model.reset_visual_history()      # as upstream's AlpaSim driver does before every call
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
            out = self.model(tiles, ctx["map_context"], ctx["visual_history"], ego_hist, route_mask=ctx["route_mask"],
                             map_valid=ctx["map_valid"], route_valid=ctx["route_valid"],
                             projection=proj, geometry_type="pinhole", camera_history_tiles=hist_tiles,
                             history_projections=hist_proj, front_camera_tile=front, front_projection=fproj,
                             mode="infer", initial_noise=self.noise, camera_fpn_cache=cache,
                             camera_fpn_stream_ids=[stream], camera_fpn_timestamps_us=[t_us],
                             front_camera_fpn_tile=front_fpn, front_camera_fpn_available=self.avail)
        return out[0] if isinstance(out, tuple) else out

    def set_rig(self, rig: dict) -> dict:
        torch = self.torch
        v = rig["vehicle"]
        self.origin, info = R.ref_origin_from_raw(v["world_matrix"], v["location"], v["wheel_positions"],
                                                  v["wheel_radii"])
        M_veh = np.asarray(v["world_matrix"], dtype=np.float64).reshape(4, 4)
        cams = rig["cameras"]
        self.specs = [{"W": int(c["width"]), "H": int(c["height"]), "hfov": float(c["fov"])} for c in cams]
        M_va = [np.linalg.inv(M_veh) @ np.asarray(c["world_matrix"], dtype=np.float64).reshape(4, 4) for c in cams]
        T_ref_opt = [R.T_ref_opt_from_actor(m, self.origin) for m in M_va]
        pose_err_mm, pose_err_deg = R.rig_mount_errors(self.cams, rig, self.origin)
        self.ref_to_cam = [np.linalg.inv(T) for T in T_ref_opt]
        self.Kt = [R.scaled_intrinsic(R.carla_intrinsic(s["W"], s["H"], s["hfov"]), (s["W"], s["H"]), (512, 512))
                   for s in self.specs]
        s0 = self.specs[0]
        Kf = R.scaled_intrinsic(R.carla_intrinsic(s0["W"], s0["H"], s0["hfov"]), (s0["W"], s0["H"]), (1024, 1024))
        P_cur = np.stack([self.Kt[i] @ self.ref_to_cam[i][:3, :] for i in range(6)])[None].astype(np.float32)
        P_front = (Kf @ self.ref_to_cam[0][:3, :])[None, None].astype(np.float32)
        self.proj = self.PinholeProjection(torch.from_numpy(P_cur).to(self.dev), geometry_type="pinhole")
        self.fproj = self.PinholeProjection(torch.from_numpy(P_front).to(self.dev), geometry_type="pinhole")
        # C2 (ICD section 10, amendments 1 and 2): the tile size handed to the checkpoint and the
        # projection operators, once per run; the agent writes them into checkpointInputs.
        c2 = R.c2_projection_block(P_cur, P_front)
        return {"engine": self.name, "origin": self.origin.tolist(), "origin_info": info, "rig_pose_err_mm": pose_err_mm,
                "rig_pose_err_deg": pose_err_deg,
                "camera_projection_matrix": P_cur.tolist(), "front_camera_projection_matrix": P_front.tolist(),
                "front_hi_res": {"width": 1024, "height": 1024}, "tile_wh": [512, 512],
                "c2_projections_json": json.dumps(c2)}

    def _rgb(self, u8):
        return u8[..., [2, 1, 0]].permute(2, 0, 1).unsqueeze(0).float().div_(255.0)

    def condition(self, k, images, shapes, M_world_veh, map_context, route_mask):
        torch, F = self.torch, self.F
        rec = {"engine": self.name}
        if all(im is not None for im in images):
            with torch.autocast("cuda", enabled=False):
                imgs = [torch.from_numpy(im).to(self.dev) for im in images]
                front = (F.interpolate(self._rgb(imgs[0]), size=(1024, 1024), mode="bilinear", align_corners=False,
                                       antialias=True) - self.mean) / self.std
                base0 = F.interpolate(front, size=(512, 512), mode="bilinear", align_corners=False, antialias=True)
                others = [(F.interpolate(self._rgb(im), size=(512, 512), mode="bilinear", align_corners=False,
                                         antialias=True) - self.mean) / self.std for im in imgs[1:]]
                self.tiles[k] = torch.cat([base0] + others, 0)
                self.fronts[k] = (front, base0)
            torch.cuda.current_stream().synchronize()   # the host buffers return to the frame store after this call
        if map_context is not None and route_mask is not None:
            mc = torch.from_numpy(np.frombuffer(map_context, dtype=np.float32).reshape(tuple(self.TPL["map_context"].shape[1:])).copy())
            rm = torch.from_numpy(np.frombuffer(route_mask, dtype=np.float32).reshape(tuple(self.TPL["route_mask"].shape[1:])).copy())
            self.nav[k] = {"map_context": mc[None].to(self.dev), "route_mask": rm[None].to(self.dev),
                           "visual_history": self.cam_only["visual_history"], "map_valid": self.nav_on,
                           "route_valid": self.nav_on}
        self.poses.add(k, R.T_world_ref(M_world_veh, self.origin))
        for ring, keep in ((self.tiles, 40), (self.fronts, 8), (self.nav, 8), (self.rows, 8)):
            for old in [j for j in ring if j < k - keep]:
                del ring[old]
        measured = H.egomotion_rows(self.poses.window(k), self.curv) if self.poses.complete(k) else None
        if measured is not None:
            self.rows[k] = measured
        primed = measured is not None and all(j in self.tiles for j in H.camera_history_frames(k) + [k])
        return primed, measured, rec

    def infer(self, k):
        torch = self.torch
        hk = H.camera_history_frames(k)
        if k not in self.rows or any(j not in self.tiles for j in hk + [k]):
            return None
        t0 = time.perf_counter()
        s = k % 5
        t_us = 10_000_000 + 100_000 * k
        last = self.caches[s].last_committed_timestamps_us
        if last is not None and last != (t_us - 500_000,):
            self.caches[s].reset()
            self.counts["gap_reset"] += 1
        hist_tiles = torch.stack([self.tiles[j] for j in hk])[None]
        Tk = self.poses.pose[k]
        hist_proj = []
        for j in hk:
            pfc = np.linalg.inv(self.poses.pose[j]) @ Tk
            hist_proj.append(np.stack([self.Kt[v] @ (self.ref_to_cam[v] @ pfc)[:3, :] for v in range(6)]).astype(np.float32))
        hp = torch.from_numpy(np.stack(hist_proj)[None]).to(self.dev)
        hproj = tuple(self.PinholeProjection(hp[:, i], geometry_type="pinhole") for i in range(7))
        measured = self.rows[k]
        eh = self.adapt(torch.from_numpy(H.checkpoint_rows(measured)).reshape(1, -1), self.policy).to(self.dev, torch.float32)
        v0 = float(measured[-1, 0])
        before = len(self.caches[s])
        front, fpn = self.fronts[k]
        out = self._call(self.tiles[k][None], front, fpn, self.proj, self.fproj, hist_tiles, hproj, eh, self.caches[s],
                         "phase%d" % s, t_us, ctx=self.nav.get(k))
        c = out.float().cpu()
        pos, head, _ = self.integrate(c.reshape(1, -1, 2), torch.tensor([v0], dtype=torch.float32))
        if before != 7:
            self.counts["reprime"] += 1
        samples = np.zeros((64, 5), dtype=np.float32)
        samples[:, 0:2] = c.reshape(-1, 2).numpy()
        samples[:, 2:4] = pos[0].numpy()
        samples[:, 4] = head[0].numpy()
        return samples, v0, {"engine": self.name, "compute_ms": round((time.perf_counter() - t0) * 1000, 2),
                             "cache_before": before, "nav": k in self.nav, "counts": dict(self.counts)}

    def close(self):
        self.outer.close()
