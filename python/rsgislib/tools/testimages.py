#!/usr/bin/env python
"""
The tools.test_images module contains some functions to create images which can be
used for testing other functions or generate example datasets

"""
import os
from typing import List
import rsgislib


def create_random_int_img(
    output_img: str,
    n_bands: int,
    x_size: int,
    y_size: int,
    out_vals: List[int],
    gdalformat: str = "KEA",
    datatype: int = rsgislib.TYPE_8UINT,
    calc_stats: bool = True,
    tmp_path: str = None,
):
    """
    A function which creates an image with pixels values randomly assigned from the
    list in the out_vals input list.

    :param output_img: The output image file name and path
    :param n_bands: the number of bands in the output image
    :param x_size: the number of pixels in the X axis
    :param y_size: the number of pixels in the Y axis
    :param out_vals: a list of values to be randomly populated within the output image
    :param gdalformat: the output image file format (Default: KEA)
    :param datatype: the output image data type (Default: rsgislib.TYPE_8UINT)
    :param calc_stats: calculate image statistics and pyramids
    :param tmp_path: Can optionally provide a temporary path where a reference
                     image will be created and then removed.

    """
    import numpy.random
    from rios import applier

    import rsgislib.imageutils
    import rsgislib.tools.utils

    uid_str = rsgislib.tools.utils.uid_generator()

    if tmp_path is None:
        tmp_path = ""

    tmp_ref_img = os.path.join(tmp_path, f"tmp_ref_img_{uid_str}.kea")

    rsgislib.imageutils.create_blank_img_py(
        tmp_ref_img,
        n_bands,
        x_size,
        y_size,
        100000,
        500000,
        1,
        1,
        "",
        "KEA",
        datatype,
        options=[],
        no_data_val=0,
    )

    try:
        progress_bar = rsgislib.TQDMProgressBar()
    except:
        from rios import cuiprogress

        progress_bar = cuiprogress.GDALProgressBar()

    infiles = applier.FilenameAssociations()
    infiles.image = tmp_ref_img
    outfiles = applier.FilenameAssociations()
    outfiles.out_image = output_img
    otherargs = applier.OtherInputs()
    otherargs.out_vals = out_vals
    aControls = applier.ApplierControls()
    aControls.progress = progress_bar
    aControls.drivername = gdalformat
    aControls.omitPyramids = True
    aControls.calcStats = False

    def _applyPopVals(info, inputs, outputs, otherargs):
        """
        This is an internal rios function
        """
        in_img_shp = inputs.image.shape
        outputs.out_image = numpy.random.choice(otherargs.out_vals, in_img_shp).astype(
            rsgislib.get_numpy_datatype(datatype)
        )

    applier.apply(_applyPopVals, infiles, outfiles, otherargs, controls=aControls)
    if calc_stats:
        import rsgislib.rastergis

        rsgislib.rastergis.pop_rat_img_stats(output_img, True, True, True)

    rsgislib.imageutils.delete_gdal_layer(tmp_ref_img)
