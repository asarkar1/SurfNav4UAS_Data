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


## Read Parquet file

* Read file
* Convert to .csv


## read mcap file


