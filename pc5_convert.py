#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import Optional, Tuple, Iterable, Set, List
from bisect import bisect

import h5py
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description="pc5 → PCD/KITTI/CSV converter")
    parser.add_argument("--pc5_path", type=str, required=True, help="PC5 file path")
    parser.add_argument(
        "--lidar_name",
        type=str,
        default="top",
        choices=["top"],
        help="Lidar sensor name",
    )
    parser.add_argument(
        "--out_dir", type=str, default="exports", help="Output directory for .pcd/.bin/.csv"
    )
    parser.add_argument(
        "--formats",
        type=str,
        help="Comma-separated list of formats to export: pcd,bin,csv. Example: --formats pcd,bin",
    )
    parser.add_argument("--to_pcd", action="store_true", help="Export PCD")
    parser.add_argument("--to_bin", action="store_true", help="Export KITTI .bin and _k.bin")
    parser.add_argument("--to_csv", action="store_true", help="Export CSV")
    parser.add_argument(
        "--frame",
        type=int,
        help="Export only this 0-based frame index. If omitted, exports ALL frames.",
    )
    return parser.parse_args()


def compute_selected_formats(formats_arg: Optional[str], to_pcd: bool, to_bin: bool, to_csv: bool) -> Set[str]:
    valid = {"pcd", "bin", "csv"}

    if formats_arg:
        parts = [p.strip().lower() for p in formats_arg.split(",") if p.strip()]
        selected = set(parts)
        unknown = selected - valid
        if unknown:
            raise ValueError(f"Unknown format(s): {', '.join(sorted(unknown))}. Valid: {', '.join(sorted(valid))}")
        return selected
    any_bool = to_pcd or to_bin or to_csv
    if any_bool:
        selected = set()
        if to_pcd:
            selected.add("pcd")
        if to_bin:
            selected.add("bin")
        if to_csv:
            selected.add("csv")
        return selected

    return valid  # default-- all


def ensure_xyzi(points_np: np.ndarray) -> np.ndarray:
    """
    Ensure Nx4 XYZI float32. If >=4 columns, use col 3 as intensity; else zeros.
    """
    if points_np.size == 0:
        return points_np.astype(np.float32)
    xyz = points_np[:, :3]
    if points_np.shape[1] >= 4:
        inten = points_np[:, 3:4]
    else:
        inten = np.zeros((points_np.shape[0], 1), dtype=points_np.dtype)
    xyzi = np.concatenate([xyz, inten], axis=1).astype(np.float32, copy=False)
    return xyzi


def load_lidar_metadata(lid_id: int) -> str:
    """
    Returns the HDF5 group path for the selected lidar.
    """
    # hardcoded config, subject to change later ...
    LIDAR = {
        "lidars": [
            {"id": "top", "msgtime-offset": 0, "ouster-packet-ros-topic": "/ouster"}
        ]
    }
    config = LIDAR["lidars"][lid_id]
    group_path = config["ouster-packet-ros-topic"].strip("/")
    return group_path


def read_xyz_refl(frame_index: Optional[int],
                  timestamp: Optional[int],
                  msgtimes: Optional[np.ndarray],
                  rnge,
                  beam_direction: np.ndarray,
                  beam_offset: np.ndarray,
                  srefl) -> Tuple[np.ndarray, np.ndarray]:
    """
    Reads the point cloud (x,y,z) and reflectivity for a given frame or timestamp.
    """
    if timestamp is not None:
        if msgtimes is None:
            raise ValueError("msgtimes must be provided when timestamp is used")
        frame_index = bisect(msgtimes, timestamp)
    assert frame_index is not None

    # meters
    data = rnge[frame_index].flatten() * 0.001
    valid = data != 0
    if not np.any(valid):
        return np.empty((0, 3), dtype=np.float32), np.empty((0,), dtype=np.float32)

    xyz = data[valid, None] * beam_direction[valid, :] + beam_offset[valid, :]
    refl = srefl[frame_index].flatten()[valid]
    return xyz.astype(np.float32, copy=False), refl.astype(np.float32, copy=False)


def create_points_array(pts: np.ndarray, refl: np.ndarray) -> Optional[np.ndarray]:
    """
    Return Nx4 XYZI float32 array with intensity normalized to [0,1].
    Assumes incoming Ouster reflectivity is 0..255 (uint8-like).
    """
    n = pts.shape[0]
    if n == 0:
        print("create_points_array: received 0 points.")
        return None
    out = np.empty((n, 4), dtype=np.float32)
    out[:, :3] = pts

    # Normalize reflectivity to 0-1
    out[:, 3] = (refl.astype(np.float32) / 255.0)
    np.clip(out[:, 3], 0.0, 1.0, out=out[:, 3])

    # Optional: drop NaNs/Infs in intensity
    mask = np.isfinite(out[:, 3])
    if not np.all(mask):
        out[:, 3][~mask] = 0.0

    return out


def save_as_pcd_binary(xyzi: np.ndarray, out_path: Path) -> None:
    """
    Write binary PCD (FIELDS x y z intensity, float32) with intensity in [0,1].
    """
    n = int(xyzi.shape[0])
    header = (
        "# .PCD v0.7 - Point Cloud Data file format\n"
        "VERSION 0.7\n"
        "FIELDS x y z intensity\n"
        "SIZE 4 4 4 4\n"
        "TYPE F F F F\n"
        "COUNT 1 1 1 1\n"
        f"WIDTH {n}\n"
        "HEIGHT 1\n"
        "VIEWPOINT 0 0 0 1 0 0 0\n"
        f"POINTS {n}\n"
        "DATA binary\n"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(header.encode("ascii"))
        f.write(xyzi.astype(np.float32, copy=False).tobytes(order="C"))


def save_as_bin(xyzi: np.ndarray, out_path: Path) -> None:
    """
    Write KITTI-style .bin (float32 XYZI).
    Intensity is expected to be in [0,1] (KITTI convention).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    xyzi.astype(np.float32, copy=False).tofile(out_path)


def save_as_csv(xyzi: np.ndarray, out_path: Path) -> None:
    """
    Write CSV with headers x,y,z,i (float32).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    header = "x,y,z,i"
    np.savetxt(out_path, xyzi, fmt="%.6f", delimiter=",", header=header, comments="")


def export_frame(
    points_xyzi: np.ndarray,
    msg_ns: int,
    out_dir: str,
    formats: Iterable[str],
) -> Optional[Tuple[str, int]]:
    """
    points_xyzi: (N, 4) np.float32 array
    msg_ns: timestamp in integer nanoseconds
    Writes <secs.nsecs>.* for selected formats
    """
    secs = msg_ns // 1_000_000_000
    nsecs = msg_ns % 1_000_000_000
    ts = f"{secs}.{nsecs:09d}"

    xyzi = ensure_xyzi(points_xyzi)
    if xyzi.shape[0] == 0:
        return None

    root = Path(out_dir)
    if "pcd" in formats:
        save_as_pcd_binary(xyzi, root / f"pcd/{ts}.pcd")
    if "bin" in formats:
        ncbin = np.zeros((xyzi.shape[0], 5), dtype=np.float32)
        ncbin[:, :4] = xyzi
        save_as_bin(ncbin, root / f"bin/{ts}.bin") # nusc needs 1x5 cells
        save_as_bin(xyzi, root / f"bin_k/{ts}.bin")  # kitti needs 1x4 cells
    if "csv" in formats:
        save_as_csv(xyzi, root / f"csv/{ts}.csv")

    return ts, int(xyzi.shape[0])


def _resolve_indices(num_frames: int, single_frame: Optional[int]) -> List[int]:
    if single_frame is None:
        return list(range(num_frames))  # full trip
    if single_frame < 0 or single_frame >= num_frames:
        raise ValueError(f"--frame {single_frame} out of range [0, {num_frames-1}]")
    return [single_frame]


def convert_pc5_frames(pc5_path: str, lidar_name: str, out_dir: str, formats: Iterable[str], frame: Optional[int]) -> None:
    """
    Iterates selected frames in the pc5 and writes requested formats for each.
    Pure NumPy pipeline; no DataContainer / Torch.
    """
    lid_id = {"top": 0}.get(lidar_name, 0)
    group_path = load_lidar_metadata(lid_id)

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    exported = 0
    with h5py.File(pc5_path, "r") as pc5:
        if group_path not in pc5:
            raise ValueError(f"HDF5 group '{group_path}' not found in {pc5_path}")
        group = pc5[group_path]

        msgtimes_raw = group["msgtimes"][:]  # uint64 nanos

        # direction/offset stored as 3xM; reshape to Mx3
        beam_direction = group["direction"][:].reshape((3, -1)).T.astype(np.float32)
        beam_offset = group["offset"][:].reshape((3, -1)).T.astype(np.float32)

        rnge = group["range"]
        srefl = group["reflectivity"]

        num_frames = int(rnge.shape[0])
        indices = _resolve_indices(num_frames, frame)

        for count, idx in enumerate(indices):
            pts, ref = read_xyz_refl(
                frame_index=idx,
                timestamp=None,
                msgtimes=None,
                rnge=rnge,
                beam_direction=beam_direction,
                beam_offset=beam_offset,
                srefl=srefl,
            )

            xyzi = create_points_array(pts, ref)
            if xyzi is None or xyzi.size == 0:
                print(f" {idx}: no valid points")
                continue

            msg_ns = int(msgtimes_raw[idx])
            res = export_frame(xyzi, msg_ns, out_dir, formats=formats)
            if res is None:
                print(f" {idx}: zero after")
                continue

            ts, npts = res
            exported += 1
            print(f"{count+1}/{len(indices)}  frame={idx} -> {ts}   ({npts} pts)")

    scope = "all frames" if frame is None else f"frame {frame}"
    print(f"exported {exported}/{len(indices)} ({scope}) to {out_dir}")


if __name__ == "__main__":
    args = parse_args()
    try:
        selected_formats = compute_selected_formats(args.formats, args.to_pcd, args.to_bin, args.to_csv)
    except ValueError as e:
        raise SystemExit(str(e))

    try:
        convert_pc5_frames(
            args.pc5_path,
            args.lidar_name,
            args.out_dir,
            formats=selected_formats,
            frame=args.frame,
        )
    except ValueError as e:
        raise SystemExit(str(e))
