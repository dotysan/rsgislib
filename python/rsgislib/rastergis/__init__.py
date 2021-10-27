#!/usr/bin/env python
"""
The Raster GIS module contains functions for attributing and manipulating raster attribute tables.
"""

# import the C++ extension into this level
from ._rastergis import *

import osgeo.gdal as gdal

import numpy

haveHDF5 = True
try:
    import h5py
except ImportError as h5Err:
    haveHDF5 = False


class BandAttStats:
    """This is passed to the populate_rat_with_stats function"""

    def __init__(
        self,
        band,
        min_field=None,
        max_field=None,
        sum_field=None,
        std_dev_field=None,
        mean_field=None,
    ):
        self.band = band
        self.min_field = min_field
        self.max_field = max_field
        self.sum_field = sum_field
        self.mean_field = mean_field
        self.std_dev_field = std_dev_field


class FieldAttStats:
    """This is passed to the calcRelDiffNeighStats function"""

    def __init__(
        self,
        field,
        min_field=None,
        max_field=None,
        sum_field=None,
        std_dev_field=None,
        mean_field=None,
    ):
        self.field = field
        self.min_field = min_field
        self.max_field = max_field
        self.sum_field = sum_field
        self.mean_field = mean_field
        self.std_dev_field = std_dev_field


class BandAttPercentiles:
    """This is passed to the populateRATWithPercentiles function"""

    def __init__(self, percentile, field_name):
        self.percentile = percentile
        self.field_name = field_name


class ShapeIndex:
    """This is passed to the calcShapeIndices function"""

    def __init__(self, col_name, idx, col_idx=0):
        self.col_name = col_name
        self.col_idx = col_idx
        self.idx = idx


def export_cols_to_gdal_image(
    clumps_img, output_img, gdalformat, datatype, fields, ratband=1, tmp_dir=None
):
    """
    Exports columns of the raster attribute table as bands in a GDAL image.
    Utility function, exports each column individually then stacks them.

    :param clumps_img: is a string containing the name of the input image file with RAT
    :param output_img: is a string containing the name of the output gdal file
    :param gdalformat: is a string containing the GDAL format for the output
                       file - eg 'KEA'
    :param datatype: is an int containing one of the values from rsgislib.TYPE_*
    :param field: is a list of strings, providing the names of the column to be exported
    :param ratband: is an optional (default = 1) integer parameter specifying the image
                    band to which the RAT is associated.

    Example:

    .. code:: python

       clumps='./RATS/injune_p142_casi_sub_utm_clumps_elim_final_clumps_elim_final.kea'
       outimage='./TestOutputs/RasterGIS/injune_p142_casi_rgb_export.kea'
       gdalformat = 'KEA'
       datatype = rsgislib.TYPE_32FLOAT
       fields = ['RedAvg','GreenAvg','BlueAvg']
       rastergis.export_cols_to_gdal_image(clumps, outimage, gdalformat,
                                           datatype, fields)

    """
    import os
    import rsgislib.tools.filetools
    from rsgislib import imageutils

    if tmp_dir is None:
        tmp_dir = os.path.split(output_img)[0]

    outExt = os.path.splitext(output_img)[-1]
    tempFileList = []

    # Export each field
    for field in fields:
        print("Exporting: " + field)
        outTempFile = os.path.join(tmp_dir, field + outExt)
        export_col_to_gdal_img(
            clumps_img, outTempFile, gdalformat, datatype, field, ratband
        )
        tempFileList.append(outTempFile)

    # Stack Bands
    print("Stacking Bands")
    imageutils.stack_img_bands(
        tempFileList, fields, output_img, None, 0, gdalformat, datatype
    )

    # Remove temp files
    print("Removing temp files")
    for tempFile in tempFileList:
        rsgislib.tools.filetools.delete_file_with_basename(tempFile)


def get_rat_length(clumps_img, rat_band=1):
    """
    A function which returns the length (i.e., number of rows) within the RAT.

    :param clumps_img: path to the image file with the RAT
    :param rat_band: the band within the image file for which the RAT is to read.
    :returns: an int with the number of rows.

    """
    # Open input image file
    clumps_img_ds = gdal.Open(clumps_img, gdal.GA_ReadOnly)
    if clumps_img_ds is None:
        raise Exception("Could not open the inputted clumps image.")

    clumps_img_band = clumps_img_ds.GetRasterBand(rat_band)
    if clumps_img_band is None:
        raise Exception("Could not open the inputted clumps image band.")

    clumps_img_rat = clumps_img_band.GetDefaultRAT()
    if clumps_img_rat is None:
        raise Exception("Could not open the inputted clumps image band RAT.")

    nrows = clumps_img_rat.GetRowCount()

    clumps_img_ds = None
    return nrows


def get_rat_columns(clumps_img, rat_band=1):
    """
    A function which returns a list of column names within the RAT.

    :param clumps_img: path to the image file with the RAT
    :param rat_band: the band within the image file for which the RAT is to read.
    :returns: list of column names.

    """
    # Open input image file
    clumps_img_ds = gdal.Open(clumps_img, gdal.GA_ReadOnly)
    if clumps_img_ds is None:
        raise Exception("Could not open the inputted clumps image.")

    clumps_img_band = clumps_img_ds.GetRasterBand(rat_band)
    if clumps_img_band is None:
        raise Exception("Could not open the inputted clumps image band.")

    clumps_img_rat = clumps_img_band.GetDefaultRAT()
    if clumps_img_rat is None:
        raise Exception("Could not open the inputted clumps image band RAT.")

    ncols = clumps_img_rat.GetColumnCount()
    col_names = []
    for col_idx in range(ncols):
        col_names.append(clumps_img_rat.GetNameOfCol(col_idx))

    clumps_img_ds = None
    return col_names


def get_rat_columns_info(clumps_img, rat_band=1):
    """
    A function which returns a dictionary of column names with type (GFT_Integer,
    GFT_Real, GFT_String) and usage (e.g., GFU_Generic, GFU_PixelCount,
    GFU_Name, etc.) within the RAT.

    :param clumps_img: path to the image file with the RAT
    :param rat_band: the band within the image file for which the RAT is to read.
    :returns: dict of column information.

    """
    # Open input image file
    clumps_img_ds = gdal.Open(clumps_img, gdal.GA_ReadOnly)
    if clumps_img_ds is None:
        raise Exception("Could not open the inputted clumps image.")

    clumps_img_band = clumps_img_ds.GetRasterBand(rat_band)
    if clumps_img_band is None:
        raise Exception("Could not open the inputted clumps image band.")

    clumps_img_rat = clumps_img_band.GetDefaultRAT()
    if clumps_img_rat is None:
        raise Exception("Could not open the inputted clumps image band RAT.")

    ncols = clumps_img_rat.GetColumnCount()
    col_info = dict()
    for col_idx in range(ncols):
        col_name = clumps_img_rat.GetNameOfCol(col_idx)
        col_type = clumps_img_rat.GetTypeOfCol(col_idx)
        col_usage = clumps_img_rat.GetUsageOfCol(col_idx)
        col_info[col_name] = dict()
        col_info[col_name]["type"] = col_type
        col_info[col_name]["usage"] = col_usage

    clumps_img_ds = None
    return col_info


def read_rat_neighbours(clumps_img, start_row=None, end_row=None, rat_band=1):
    """
    A function which returns a list of clumps neighbours from a KEA RAT. Note, the
    neighbours are popualted using the function rsgislib.rastergis.findNeighbours.
    By default the whole datasets of neightbours is read to memory but the start_row
    and end_row variables can be used to read a subset of the RAT.

    :param clumps_img: path to the image file with the RAT
    :param start_row: the row within the RAT to start reading, if None will start
                      at 0 (Default: None).
    :param end_row: the row within the RAT to end reading, if None will end at n_rows
                    within the RAT. (Default: None)
    :param rat_band: the band within the image file for which the RAT is to read.
    :returns: list of lists with neighbour indexes.
    """
    if not haveHDF5:
        raise Exception("Need the h5py library for this function")

    # Check that 'NumNeighbours' column exists
    rat_columns = get_rat_columns(clumps_img, rat_band)
    if "NumNeighbours" not in rat_columns:
        raise Exception(
            "Clumps image RAT does not contain 'NumNeighbours' "
            "column - have you populated neightbours?"
        )

    n_rows = get_rat_length(clumps_img)

    if start_row is None:
        start_row = 0

    if end_row is None:
        end_row = n_rows

    clumps_h5_file = h5py.File(clumps_img)
    neighbours_path = "BAND{}/ATT/NEIGHBOURS/NEIGHBOURS".format(rat_band)
    neighbours = clumps_h5_file[neighbours_path]
    neighbours_data = neighbours[start_row:end_row]
    clumps_h5_file = None
    return neighbours_data


def check_string_col_valid(
    clumps_img,
    str_col,
    rm_punc=False,
    rm_spaces=False,
    rm_non_ascii=False,
    rm_dashs=False,
):
    """
    A function which checks a string column to ensure nothing is invalid.

    :param clumps_img: input clumps image.
    :param str_col: the column to check
    :param rm_punc: If True removes punctuation from column name other
                    than dashs and underscores.
    :param rm_spaces: If True removes spaces from the column name, replacing
                      them with underscores.
    :param rm_non_ascii: If True removes characters which are not in the
                         ascii range of characters.
    :param rm_dashs: If True then dashs are removed from the column name.

    """
    import numpy
    import rsgislib.tools.utils
    from rios import ratapplier

    def _ratapplier_check_string_col_valid(info, inputs, outputs, otherargs):
        str_col_vals = getattr(inputs.inrat, otherargs.str_col)
        out_col_vals = numpy.empty_like(str_col_vals)
        for i in range(str_col_vals.shape[0]):
            try:
                str_val_tmp = str_col_vals[i].decode("utf-8")
            except:
                str_val_tmp = ""
            str_val_tmp = str_val_tmp.strip()
            str_val_tmp = rsgislib.tools.utils.check_str(
                str_val_tmp,
                rm_non_ascii=rm_non_ascii,
                rm_dashs=rm_dashs,
                rm_spaces=rm_spaces,
                rm_punc=rm_punc,
            )
            out_col_vals[i] = str_val_tmp
        setattr(outputs.outrat, otherargs.str_col, out_col_vals)

    in_rats = ratapplier.RatAssociations()
    out_rats = ratapplier.RatAssociations()

    in_rats.inrat = ratapplier.RatHandle(clumps_img)
    out_rats.outrat = ratapplier.RatHandle(clumps_img)

    otherargs = ratapplier.OtherArguments()
    otherargs.str_col = str_col

    ratapplier.apply(_ratapplier_check_string_col_valid, in_rats, out_rats, otherargs)
