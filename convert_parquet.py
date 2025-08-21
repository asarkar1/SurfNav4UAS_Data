import json
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.csv as pacsv

def flatten_structs(table: pa.Table) -> pa.Table:
    t = table
    while any(pa.types.is_struct(f.type) for f in t.schema):
        t = t.flatten()
    return t

def stringify_nested(arr: pa.ChunkedArray) -> pa.ChunkedArray:
    t = arr.type
    if (pa.types.is_list(t) or pa.types.is_large_list(t) or pa.types.is_fixed_size_list(t) or
        pa.types.is_struct(t) or pa.types.is_map(t) or pa.types.is_union(t)):
        # element-wise JSON per row
        def to_json_chunk(chunk: pa.Array) -> pa.Array:
            py_vals = [None if v is None else v.as_py() for v in chunk]
            return pa.array([None if v is None else json.dumps(v) for v in py_vals], type=pa.string())
        return pa.chunked_array([to_json_chunk(c) for c in arr.chunks], type=pa.string())
    if pa.types.is_binary(t) or pa.types.is_large_binary(t) or pa.types.is_decimal(t):
        return pa.compute.cast(arr, pa.string())
    return arr

def parse_args():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--parquet_path", type=str)
    p.add_argument("--out_csv", type=str)
    p.add_argument("--selected_cols", nargs="*", default=None)
    return p.parse_args()

def main():
    a = parse_args()
    tbl = pq.read_table(a.parquet_path)
    tbl = flatten_structs(tbl)

    use_names = tbl.column_names if a.selected_cols is None else [c for c in a.selected_cols if c in tbl.column_names]
    missing = [] if a.selected_cols is None else [c for c in a.selected_cols if c not in tbl.column_names]
    if missing:
        print(f"Warning: missing columns skipped: {missing}")

    arrays = []
    for name in use_names:
        col = tbl.column(name)
        col = stringify_nested(col).combine_chunks()
        arrays.append(col)
    out = pa.Table.from_arrays(arrays, names=use_names)

    # Verify lengths match original
    if out.num_rows != tbl.num_rows:
        raise RuntimeError(f"Row count changed ({out.num_rows} vs {tbl.num_rows}); refusing to write CSV.")

    pacsv.write_csv(out, a.out_csv)
    print(f"Wrote: {a.out_csv} with {out.num_rows} rows and {len(use_names)} columns.")

if __name__ == "__main__":
    main()
