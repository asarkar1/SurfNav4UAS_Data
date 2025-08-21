import argparse
import os
import h5py
import numpy as np
import torch
from bisect import bisect
import pandas as pd
 
def parse_args():
    parser = argparse.ArgumentParser(description='PC5 file reader')
    parser.add_argument('--pc5_path', type=str, required=True, help='PC5 file path')
    parser.add_argument('--lidar_name', type=str, default='top', help='Lidar sensor name')
    parser.add_argument('--frame_number', type=int, default=0, help='Frame number to read')
    parser.add_argument('--export_ts', type=str, default=None, help='timestampt path and name')
    return parser.parse_args()
 
def load_lidar_data(pc5_path, lid_id):
    """
    Loads the necessary data from the HDF5 (.pc5) file.
    """
    # This configuration is hardcoded as per the original script
    LIDAR = {
        "lidars": [
            {"id": "top", "msgtime-offset": 0, "ouster-packet-ros-topic": "/ouster"}
        ]
    }
    config = LIDAR['lidars'][lid_id]
    pc5 = h5py.File(pc5_path, 'r')
    group_path = config['ouster-packet-ros-topic'].strip('/')
    group = pc5[group_path]
    return config, group
 
def read_xyz_refl(frame_index, timestamp, msgtimes, rnge, beam_direction, beam_offset, srefl):
    """
    Reads the point cloud data (x, y, z) and reflectivity for a given frame.
    """
    frame_index = bisect(msgtimes, timestamp) if timestamp is not None else frame_index
    data = rnge[frame_index].flatten() * 0.001
    valid = data != 0
    xyz = data[valid, None] * beam_direction[valid, :] + beam_offset[valid, :]
    refl = srefl[frame_index].flatten()[valid]
    return xyz, refl
 
def create_points_tensor(pts, refl):
    """
    Creates a PyTorch tensor from the point cloud and reflectivity data.
    """
    if pts.shape[0] == 0:
        print("create_points_tensor: received 0 points.")
        return None
    num_points = pts.shape[0]
    points_tensor = np.zeros((num_points, 5))
    points_tensor[:, :3] = pts
    points_tensor[:, 3:] = refl[:, None] / 256
    return torch.tensor(points_tensor, dtype=torch.float32)
 
def read_pc5_frame(pc5_path, lid_name, frame_number, timestamps = None):
    """
    Performs the core PC5 file reading functionality.
 
    Args:
        pc5_path (str): Path to the .pc5 file.
        lid_name (str): The name of the lidar sensor (e.g., 'left').
        frame_number (int): The index of the frame to read.
 
    Returns:
        tuple: A tuple containing a torch.Tensor of points (x, y, z, reflectivity,
               something_else) and the timestamp in nanoseconds, or None if
               the frame is empty.
    """
    lid_id = {'top': 0}.get(lid_name, 0)
    config, group = load_lidar_data(pc5_path, lid_id)
 
    msgtimes = 1e-9 * group['msgtimes'][:] - config['msgtime-offset']
    beam_direction = group['direction'][:].reshape((3, -1)).T.astype(np.float32)
    beam_offset = group['offset'][:].reshape((3, -1)).T.astype(np.float32)
    msgtimes_raw = group['msgtimes'][:]  # uint64 nanoseconds
    if timestamps:
        return group['msgtimes'][:]
    rnge = group['range']
    srefl = group['reflectivity']
 
    try:
        pts, ref = read_xyz_refl(
            frame_index=frame_number,
            timestamp=None,
            msgtimes=msgtimes,
            rnge=rnge,
            beam_direction=beam_direction,
            beam_offset=beam_offset,
            srefl=srefl
        )
        pts_tensor = create_points_tensor(pts, ref)
        if pts_tensor is None:
            return None, None
        return pts_tensor, int(msgtimes_raw[frame_number])
    except IndexError:
        print(f"Error: Frame {frame_number} is out of range.")
        return None, None
 
def main():
    args = parse_args()
    if not os.path.exists(args.pc5_path):
        print(f"Error: PC5 file not found at {args.pc5_path}")
        return
    if args.export_ts:
        msgs_ts = read_pc5_frame(args.pc5_path, args.lidar_name, args.frame_number, True)
        np.savetxt(args.export_ts, msgs_ts, delimiter=",", fmt='%d', header="msgtimes_ns", comments='')
        print(f"saved {len(msgs_ts)} timestamps to {args.export_ts}")
    else:
        points_tensor, timestamp = read_pc5_frame(args.pc5_path, args.lidar_name, args.frame_number)
 
        if points_tensor is not None:
            print(f"frame {args.frame_number} ")
            print(f"timestamp: {timestamp}")
            print(f"tensor: {points_tensor.shape}")
            print("5 points:\n", points_tensor[:5].numpy())
        else:
            print(f"Failed {args.frame_number}")
 
if __name__ == '__main__':
    main()
 
