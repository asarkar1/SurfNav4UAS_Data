# SurfNav4UAS_Data


## Description of the sensor suite

### Cameras:

The system has four cameras. Each cameras have ressolution of and frame rate of 60 fps. It covers 180 degree field of view. 

* Forward - 
* Forward-zoom
* Left
* Right

Camera Intrinsic
  



### LiDAR: .pc5 file. It contains:
* point cloud
* IR images


### Novatel

* novatel__oem7__bestgnsspos.parquet,
* novatel__oem7__bestgnssvel.parquet,
* novatel__oem7__bestpos.parquet,
* novatel__oem7__bestutm.parquet,
* novatel__oem7__bestvel.parquet,
* novatel__oem7__corrimu.parquet,
* novatel__oem7__fix.parquet,
* novatel__oem7__gps.parquet,
* novatel__oem7__heading2.parquet,
* novatel__oem7__imu__data_raw.parquet,
* novatel__oem7__imu__data.parquet,
* novatel__oem7__inspva.parquet,
* novatel__oem7__inspvax.parquet,
* novatel__oem7__insstdev.parquet,
* novatel__oem7__odom.parquet,
* novatel__oem7__ppppos.parquet,
* novatel__oem7__terrastarinfo.parquet,
* novatel__oem7__terrastarstatus.parquet,
* novatel__oem7__time.parquet


## Intrinsic 

## Extrinsic/ transformation

# Support code

## Read LiDAR file

* point cloud
* IR image
* timestamp
* index file from LiDAR


## Converting Parquet Files to CSV

We provide the `convert_parquet.py` script for converting Parquet files into CSV format.  
The script supports two modes:

1. **Convert the entire Parquet file** — all columns will be exported to CSV.  
2. **Convert only selected columns** — only the specified columns will be exported.

---
### 1. Convert the whole Parquet file to CSV

```bash
python convert_parquet.py --parquet_path /path/to/input.parquet --out_csv /path/to/output.csv
```
Example:
```bash
python convert_parquet.py --parquet_path data/sample.parquet --out_csv data/sample.csv
```
This will export **all columns** from `sample.parquet` into `sample.csv`.

### 2. Convert only selected columns to CSV

```bash
python convert_parquet.py --parquet_path /path/to/input.parquet --out_csv /path/to/output.csv --selected_cols col1 col2 col3
```

Example:
```bash
python convert_parquet.py --parquet_path data/sample.parquet --out_csv data/sample_subset.csv --selected_cols buffer_number timestamp
```
This will export only the columns `buffer_number` and `timestamp` into `sample_subset.csv`.

### Argument Details
- **`--parquet_path`** *(positional)* — Path to the input Parquet file to be converted.  
- **`--out_csv`** *(positional)* — Path to the output CSV file to be created.  
- **`--selected_cols`** *(optional)* — Space-separated list of column names to export.  
  - If omitted, **all columns** in the Parquet file are exported.  
  - Column order in the CSV will match the order provided here.

---

### Additional Notes
- If a column name in `--selected_cols` is not found in the Parquet file, it will be skipped and a warning will be printed.
---

### Requirements
Make sure the following Python packages are installed before running the script:

```bash
pip install pyarrow
```
The script also uses Python's built-in `json` and `argparse` modules, which do not require installation.

---
## read mcap file


