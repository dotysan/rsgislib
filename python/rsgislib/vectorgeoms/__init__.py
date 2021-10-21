#!/usr/bin/env python
"""
The vector geometries module performs geometric operations on vectors.
"""

import os
import math

import osgeo.gdal as gdal
import osgeo.ogr as ogr

import tqdm

import rsgislib.vectorutils

gdal.UseExceptions()


def convert_polygon_to_polyline(
    vec_poly_file,
    vec_poly_lyr,
    vec_line_file,
    vec_line_lyr=None,
    out_format="GPKG",
    del_exist_vec=False,
):
    """
    A function to convert a polygon vector file to a polyline file.

    :param vec_poly_file: Input polygon vector file
    :param vec_poly_lyr: The name of the vector layer
    :param vec_line_file: The output vector file
    :param vec_line_lyr: The output vector layer name
    :param out_format: The output vector file format (default: GPKG).
    :param del_exist_vec: remove output file if it exists.

    """

    if os.path.exists(vec_line_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(vec_line_file)
        else:
            raise Exception(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(vec_line_file)
            )

    if vec_line_lyr is None:
        vec_line_lyr = os.path.splitext(os.path.basename(vec_line_file))[0]

    gdal.UseExceptions()
    vec_poly_ds_obj = gdal.OpenEx(vec_poly_file, gdal.OF_VECTOR)
    vec_poly_lyr_obj = vec_poly_ds_obj.GetLayer(vec_poly_lyr)
    vec_poly_spat_ref = vec_poly_lyr_obj.GetSpatialRef()

    out_vec_drv = gdal.GetDriverByName(out_format)
    if out_vec_drv == None:
        raise Exception("Driver ('{}') has not be recognised.".format(out_format))

    out_ds_obj = out_vec_drv.Create(vec_line_file, 0, 0, 0, gdal.GDT_Unknown)
    out_lyr_obj = out_ds_obj.CreateLayer(
        vec_line_lyr, vec_poly_spat_ref, geom_type=ogr.wkbLineString
    )
    feat_defn = out_lyr_obj.GetLayerDefn()

    n_feats = vec_poly_lyr_obj.GetFeatureCount(True)
    pbar = tqdm.tqdm(total=n_feats)
    open_transaction = False
    counter = 0
    in_feature = vec_poly_lyr_obj.GetNextFeature()
    while in_feature:
        if not open_transaction:
            out_lyr_obj.StartTransaction()
            open_transaction = True

        geom = in_feature.GetGeometryRef()
        if geom is not None:
            ring = geom.GetGeometryRef(0)
            out_feat = ogr.Feature(feat_defn)
            out_feat.SetGeometry(ring)
            out_lyr_obj.CreateFeature(out_feat)
            out_feat = None

        if ((counter % 20000) == 0) and open_transaction:
            out_lyr_obj.CommitTransaction()
            open_transaction = False

        in_feature = vec_poly_lyr_obj.GetNextFeature()
        counter = counter + 1
        pbar.update(1)

    if open_transaction:
        out_lyr_obj.CommitTransaction()
        open_transaction = False
    pbar.close()
    out_lyr_obj.SyncToDisk()
    out_ds_obj = None


def get_pt_on_line(pt1, pt2, dist):
    """
    A function that calculates a point on the vector defined by pt1 and pt2.

    :param pt1: An ogr point geometry which has functions GetX() and GetY().
    :param pt2: An ogr point geometry which has functions GetX() and GetY().
    :param dist: The distance from pt1 the new point is to be created.
    :return: The created point; returned as a set of floats: (x, y)

    """
    import math

    out_pt_x = 0.0
    out_pt_y = 0.0
    if dist == 0:
        out_pt_x = pt1.GetX()
        out_pt_y = pt1.GetY()
    else:
        dx = pt2.GetX() - pt1.GetX()
        dy = pt2.GetY() - pt1.GetY()
        theta = math.atan(dy / dx)
        y1 = dist * math.sin(theta)
        x1 = dist * math.cos(theta)

        if (dx >= 0) and (dy > 0):
            out_pt_x = pt1.GetX() + x1
            out_pt_y = pt1.GetY() + y1
        elif (dx >= 0) and (dy <= 0):
            out_pt_x = pt1.GetX() + x1
            out_pt_y = pt1.GetY() + y1
        elif (dx < 0) & (dy > 0):
            out_pt_x = pt1.GetX() - x1
            out_pt_y = pt1.GetY() - y1
        elif (dx < 0) & (dy <= 0):
            out_pt_x = pt1.GetX() - x1
            out_pt_y = pt1.GetY() - y1
    return out_pt_x, out_pt_y


def find_pt_to_side(pt_start, pt, pt_end, line_len, left_hand=False):
    """
    A function to calculate a point location at a right-angle to the vector defined
    by the points pt_start and pt_end at the location pt.

    :param pt_start: An ogr point geometry which has functions GetX(), GetY() and
                     Distance().
    :param pt: An ogr point geometry which has functions GetX(), GetY() and Distance().
    :param pt_end: An ogr point geometry which has functions GetX(), GetY() and
                   Distance().
    :param line_len: The distance from the pt_start and pt_end vector to the new point.
    :param left_hand: Specify which side the point is projected from the pt_start
                      and pt_end vector. Default: False - project right-hand side of
                      vector, True - project left-hand side of vector
    :return: The created point; returned as a set of floats: (x, y)

    """
    if left_hand:
        tmp_pt = pt_end
        pt_end = pt_start
        pt_start = tmp_pt
    import math

    dx = pt_end.GetX() - pt_start.GetX()
    dy = pt_end.GetY() - pt_start.GetY()
    beta = math.atan(dy / dx)

    distanceP1P2 = pt_start.Distance(pt)
    distanceP1P3 = math.sqrt((line_len * line_len) + (distanceP1P2 * distanceP1P2))
    theta = math.atan(line_len / distanceP1P2)
    alpha = math.pi - (theta - beta)

    localX = distanceP1P3 * math.cos(alpha)
    localY = distanceP1P3 * math.sin(alpha)

    if (dx >= 0) and (dy > 0):
        out_pt_x = pt_start.GetX() - localX
        out_pt_y = pt_start.GetY() - localY
    elif (dx >= 0) and (dy <= 0):
        out_pt_x = pt_start.GetX() - localX
        out_pt_y = pt_start.GetY() - localY
    elif (dx < 0) and (dy > 0):
        out_pt_x = pt_start.GetX() + localX
        out_pt_y = pt_start.GetY() + localY
    elif (dx < 0) and (dy <= 0):
        out_pt_x = pt_start.GetX() + localX
        out_pt_y = pt_start.GetY() + localY
    else:
        raise Exception("Could not resolve find_pt_to_side...")
    return out_pt_x, out_pt_y


def create_orthg_lines(
    in_vec_file,
    in_vec_lyr,
    out_vec_file,
    out_vec_lyr=None,
    pt_step=1000,
    line_len=10000,
    left_hand=False,
    out_format="GPKG",
    del_exist_vec=False,
):
    """
    A function to create a set of lines which are orthogonal to the lines of the input
    vector file.

    :param in_vec_file: The inputted vector file path - this should be a
                        polyline vector file
    :param in_vec_lyr: The name of the vector layer
    :param out_vec_file: The output vector file path - this will be a polyline
                         vector file
    :param out_vec_lyr: The name of the output vector layer (if None then created
                        as the same as the file name)
    :param pt_step: The steps (in the unit of the coordinate system) along lines
                    in the layer at which lines are created.
    :param line_len: The length of the lines created.
    :param left_hand: Specify which side the point is projected from the line
                      (i.e., left or right side)
                      Default: False - project right-hand side of vector, True -
                      project left-hand side of vector
    :param out_format: The output file format of the vector file.
    :param del_exist_vec: remove output file if it exists.

    """
    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise Exception(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(out_vec_file)
            )

    if out_vec_lyr is None:
        out_vec_lyr = os.path.splitext(os.path.basename(out_vec_file))[0]

    gdal.UseExceptions()
    vec_ds_obj = gdal.OpenEx(in_vec_file, gdal.OF_VECTOR)
    if vec_ds_obj is None:
        raise Exception("Could not open vector file: {}".format(in_vec_file))
    vec_lyr_obj = vec_ds_obj.GetLayer(in_vec_lyr)
    if vec_lyr_obj is None:
        raise Exception("Could not open vector layer: {}".format(in_vec_lyr))
    vec_spat_ref = vec_lyr_obj.GetSpatialRef()

    out_vec_drv = gdal.GetDriverByName(out_format)
    if out_vec_drv == None:
        raise Exception("Driver ('{}') has not be recognised.".format(out_format))

    out_ds_obj = out_vec_drv.Create(out_vec_file, 0, 0, 0, gdal.GDT_Unknown)
    out_lyr_obj = out_ds_obj.CreateLayer(
        out_vec_lyr, vec_spat_ref, geom_type=ogr.wkbLineString
    )
    uid_field = ogr.FieldDefn("uid", ogr.OFTInteger)
    out_lyr_obj.CreateField(uid_field)
    start_x_field = ogr.FieldDefn("start_x", ogr.OFTReal)
    out_lyr_obj.CreateField(start_x_field)
    start_y_field = ogr.FieldDefn("start_y", ogr.OFTReal)
    out_lyr_obj.CreateField(start_y_field)
    end_x_field = ogr.FieldDefn("end_x", ogr.OFTReal)
    out_lyr_obj.CreateField(end_x_field)
    end_y_field = ogr.FieldDefn("end_y", ogr.OFTReal)
    out_lyr_obj.CreateField(end_y_field)
    feat_defn = out_lyr_obj.GetLayerDefn()

    n_feats = vec_lyr_obj.GetFeatureCount(True)
    pbar = tqdm.tqdm(total=n_feats)
    open_transaction = False
    counter = 0
    line_uid = 1
    p_pt = ogr.Geometry(ogr.wkbPoint)
    p_pt.AddPoint(0.0, 0.0)
    c_pt = ogr.Geometry(ogr.wkbPoint)
    c_pt.AddPoint(0.0, 0.0)
    c_dist = 0.0
    first_pt = True
    in_feature = vec_lyr_obj.GetNextFeature()
    while in_feature:
        if not open_transaction:
            out_lyr_obj.StartTransaction()
            open_transaction = True

        geom = in_feature.GetGeometryRef()
        if geom is not None:
            pts = geom.GetPoints()
            first_pt = True
            c_dist = 0.0
            for pt in pts:
                if first_pt:
                    p_pt.SetPoint(0, pt[0], pt[1])
                    c_pt.SetPoint(0, pt[0], pt[1])
                    first_pt = False
                else:
                    p_pt.SetPoint(0, c_pt.GetX(), c_pt.GetY())
                    c_pt.SetPoint(0, pt[0], pt[1])
                    n_step = 0
                    step_c_dist = c_dist
                    while True:
                        if (
                            (p_pt.Distance(c_pt) + step_c_dist) - (pt_step * n_step)
                        ) > pt_step:
                            pt_at_dist = ((pt_step * n_step) + pt_step) - step_c_dist
                            ptx, pty = get_pt_on_line(p_pt, c_pt, pt_at_dist)
                            base_pt = ogr.Geometry(ogr.wkbPoint)
                            base_pt.AddPoint(ptx, pty)
                            ptx_end, pty_end = find_pt_to_side(
                                p_pt, base_pt, c_pt, line_len, left_hand
                            )
                            out_line = ogr.Geometry(ogr.wkbLineString)
                            out_line.AddPoint(ptx, pty)
                            out_line.AddPoint(ptx_end, pty_end)
                            out_feat = ogr.Feature(feat_defn)
                            out_feat.SetGeometry(out_line)
                            out_feat.SetField("uid", line_uid)
                            out_feat.SetField("start_x", ptx)
                            out_feat.SetField("start_y", pty)
                            out_feat.SetField("end_x", ptx_end)
                            out_feat.SetField("end_y", pty_end)
                            out_lyr_obj.CreateFeature(out_feat)
                            out_feat = None
                            line_uid = line_uid + 1
                            n_step = n_step + 1
                        else:
                            if n_step == 0:
                                c_dist = c_dist + p_pt.Distance(c_pt)
                            else:
                                c_dist = (p_pt.Distance(c_pt) + step_c_dist) - (
                                    pt_step * n_step
                                )
                            break

        if ((counter % 20000) == 0) and open_transaction:
            out_lyr_obj.CommitTransaction()
            open_transaction = False

        in_feature = vec_lyr_obj.GetNextFeature()
        counter = counter + 1
        pbar.update(1)

    if open_transaction:
        out_lyr_obj.CommitTransaction()
        open_transaction = False
    pbar.close()
    out_lyr_obj.SyncToDisk()
    out_ds_obj = None
    vec_ds_obj = None


def closest_line_intersection(
    vec_line_file,
    vec_line_lyr,
    vec_objs_file,
    vec_objs_lyr,
    out_vec_file,
    out_vec_lyr=None,
    start_x_field="start_x",
    start_y_field="start_y",
    uid_field="uid",
    out_format="GEOJSON",
    del_exist_vec=False,
):
    """
    A function which intersects each line within the input vector layer
    (vec_objs_file, vec_objs_lyr) creating a new line between the start
    point of the input layer (defined in the vector attribute table:
    start_x_field, start_y_field) and the intersection point which is
    closest to the start point.

    :param vec_line_file: Input lines vector file path.
    :param vec_line_lyr: Input lines vector layer name.
    :param vec_objs_file: The vector file for the objects (expecting polygons)
                          to be intersected with.
    :param vec_objs_lyr: The vector layer for the objects (expecting polygons)
                         to be intersected with.
    :param out_vec_file: The output vector file path.
    :param out_vec_lyr: The output vector layer name
    :param start_x_field: The field name for the start point X coordinate for
                          the input lines.
    :param start_y_field: The field name for the start point Y coordinate for
                          the input lines.
    :param uid_field: The field name for the Unique ID (UID) of the input lines.
    :param out_format: The output file format of the vector file.
    :param del_exist_vec: remove output file if it exists.

    """
    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise Exception(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(out_vec_file)
            )

    if out_vec_lyr is None:
        out_vec_lyr = os.path.splitext(os.path.basename(out_vec_file))[0]

    gdal.UseExceptions()
    vec_bbox = rsgislib.vectorutils.get_vec_layer_extent(vec_line_file, vec_line_lyr)

    ds_line_vec = gdal.OpenEx(vec_line_file, gdal.OF_READONLY)
    if ds_line_vec is None:
        raise Exception("Could not open '{}'".format(vec_line_file))

    lyr_line_vec = ds_line_vec.GetLayerByName(vec_line_lyr)
    if lyr_line_vec is None:
        raise Exception("Could not find layer '{}'".format(vec_line_lyr))

    x_col_exists = False
    y_col_exists = False
    uid_col_exists = False
    lyr_line_defn = lyr_line_vec.GetLayerDefn()
    for i in range(lyr_line_defn.GetFieldCount()):
        if lyr_line_defn.GetFieldDefn(i).GetName() == start_x_field:
            x_col_exists = True
        if lyr_line_defn.GetFieldDefn(i).GetName() == start_y_field:
            y_col_exists = True
        if lyr_line_defn.GetFieldDefn(i).GetName() == uid_field:
            uid_col_exists = True
        if x_col_exists and y_col_exists and uid_col_exists:
            break

    if (not x_col_exists) or (not y_col_exists) or (not uid_col_exists):
        ds_line_vec = None
        raise Exception(
            "The start x and y columns and/or UID column "
            "are not present within the input file."
        )

    ds_objs_vec = gdal.OpenEx(vec_objs_file, gdal.OF_READONLY)
    if ds_objs_vec is None:
        raise Exception("Could not open '{}'".format(vec_objs_file))

    lyr_objs_vec = ds_objs_vec.GetLayerByName(vec_objs_lyr)
    if lyr_objs_vec is None:
        raise Exception("Could not find layer '{}'".format(vec_objs_lyr))

    ds_objs_sub_vec, lyr_objs_sub_vec = rsgislib.vectorutils.subsetEnvsVecLyrObj(
        lyr_objs_vec, vec_bbox
    )

    spat_ref = lyr_objs_vec.GetSpatialRef()

    out_driver = ogr.GetDriverByName(out_format)
    out_ds_obj = out_driver.CreateDataSource(out_vec_file)
    out_lyr_obj = out_ds_obj.CreateLayer(
        out_vec_lyr, spat_ref, geom_type=ogr.wkbLineString
    )
    uid_field_obj = ogr.FieldDefn("uid", ogr.OFTInteger)
    out_lyr_obj.CreateField(uid_field_obj)
    length_field = ogr.FieldDefn("len", ogr.OFTReal)
    out_lyr_obj.CreateField(length_field)
    feat_defn = out_lyr_obj.GetLayerDefn()

    geom_collect = ogr.Geometry(ogr.wkbGeometryCollection)
    n_obj_feats = lyr_objs_sub_vec.GetFeatureCount(True)
    geom_pbar = tqdm.tqdm(total=n_obj_feats, leave=True)
    in_obj_feat = lyr_objs_sub_vec.GetNextFeature()
    while in_obj_feat:
        geom = in_obj_feat.GetGeometryRef()
        if geom is not None:
            boundary = geom.Boundary()
            geom_collect.AddGeometry(boundary)
        in_obj_feat = lyr_objs_sub_vec.GetNextFeature()
        geom_pbar.update(1)
    geom_pbar.close()

    n_feats = lyr_line_vec.GetFeatureCount(True)
    pbar = tqdm.tqdm(total=n_feats, leave=True)
    open_transaction = False
    counter = 0
    in_feature = lyr_line_vec.GetNextFeature()
    while in_feature:
        pbar.update(1)
        if not open_transaction:
            out_lyr_obj.StartTransaction()
            open_transaction = True

        line_geom = in_feature.GetGeometryRef()
        if line_geom is not None:
            uid_str = in_feature.GetField(uid_field)
            start_pt_x = in_feature.GetField(start_x_field)
            start_pt_y = in_feature.GetField(start_y_field)
            start_pt = ogr.Geometry(ogr.wkbPoint)
            start_pt.AddPoint(start_pt_x, start_pt_y)

            inter_geom = geom_collect.Intersection(line_geom)

            if (inter_geom is not None) and (inter_geom.GetGeometryCount() > 0):
                min_dist_pt_x = 0.0
                min_dist_pt_y = 0.0
                min_dist = 0.0
                c_pt = ogr.Geometry(ogr.wkbPoint)
                c_pt.AddPoint(0.0, 0.0)
                first_dist = True
                for i in range(inter_geom.GetGeometryCount()):
                    c_geom = inter_geom.GetGeometryRef(i)
                    pts = c_geom.GetPoints()
                    for pt in pts:
                        c_pt.SetPoint(0, pt[0], pt[1])
                        if first_dist:
                            min_dist = start_pt.Distance(c_pt)
                            min_dist_pt_x = pt[0]
                            min_dist_pt_y = pt[1]
                            first_dist = False
                        else:
                            pt_dist = start_pt.Distance(c_pt)
                            if pt_dist < min_dist:
                                min_dist = pt_dist
                                min_dist_pt_x = pt[0]
                                min_dist_pt_y = pt[1]
                out_line = ogr.Geometry(ogr.wkbLineString)
                out_line.AddPoint(start_pt_x, start_pt_y)
                out_line.AddPoint(min_dist_pt_x, min_dist_pt_y)
                out_feat = ogr.Feature(feat_defn)
                out_feat.SetGeometry(out_line)
                out_feat.SetField("uid", uid_str)
                out_feat.SetField("len", min_dist)
                out_lyr_obj.CreateFeature(out_feat)
                out_feat = None

        if ((counter % 20000) == 0) and open_transaction:
            out_lyr_obj.CommitTransaction()
            open_transaction = False

        in_feature = lyr_line_vec.GetNextFeature()
        counter = counter + 1

    if open_transaction:
        out_lyr_obj.CommitTransaction()
        open_transaction = False
    pbar.close()
    out_lyr_obj.SyncToDisk()
    out_ds_obj = None
    ds_line_vec = None
    ds_objs_vec = None
    ds_objs_sub_vec = None


def line_intersection_range(
    vec_line_file,
    vec_line_lyr,
    vec_objs_file,
    vec_objs_lyr,
    out_vec_file,
    out_vec_lyr=None,
    start_x_field="start_x",
    start_y_field="start_y",
    uid_field="uid",
    out_format="GEOJSON",
    del_exist_vec=False,
):
    """
    A function which intersects each line within the input vector layer
    (vec_objs_file, vec_objs_lyr) creating a new line between the closest
    intersection to the start point of the input layer (defined in the vector
    attribute table: start_x_field, start_y_field) and the intersection point
    which is furthest to the start point.

    :param vec_line_file: Input lines vector file path.
    :param vec_line_lyr: Input lines vector layer name.
    :param vec_objs_file: The vector file for the objects (expecting polygons)
                          to be intersected with.
    :param vec_objs_lyr: The vector layer for the objects (expecting polygons)
                         to be intersected with.
    :param out_vec_file: The output vector file path.
    :param out_vec_lyr: The output vector layer name
    :param start_x_field: The field name for the start point X coordinate for
                          the input lines.
    :param start_y_field: The field name for the start point Y coordinate for
                          the input lines.
    :param uid_field: The field name for the Unique ID (UID) of the input lines.
    :param out_format: The output file format of the vector file.
    :param del_exist_vec: remove output file if it exists.

    """
    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise Exception(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(out_vec_file)
            )

    if out_vec_lyr is None:
        out_vec_lyr = os.path.splitext(os.path.basename(out_vec_file))[0]

    gdal.UseExceptions()
    vec_bbox = rsgislib.vectorutils.get_vec_layer_extent(vec_line_file, vec_line_lyr)

    ds_line_vec = gdal.OpenEx(vec_line_file, gdal.OF_READONLY)
    if ds_line_vec is None:
        raise Exception("Could not open '{}'".format(vec_line_file))

    lyr_line_vec = ds_line_vec.GetLayerByName(vec_line_lyr)
    if lyr_line_vec is None:
        raise Exception("Could not find layer '{}'".format(vec_line_lyr))

    x_col_exists = False
    y_col_exists = False
    uid_col_exists = False
    lyr_line_defn = lyr_line_vec.GetLayerDefn()
    for i in range(lyr_line_defn.GetFieldCount()):
        if lyr_line_defn.GetFieldDefn(i).GetName() == start_x_field:
            x_col_exists = True
        if lyr_line_defn.GetFieldDefn(i).GetName() == start_y_field:
            y_col_exists = True
        if lyr_line_defn.GetFieldDefn(i).GetName() == uid_field:
            uid_col_exists = True
        if x_col_exists and y_col_exists and uid_col_exists:
            break

    if (not x_col_exists) or (not y_col_exists) or (not uid_col_exists):
        ds_line_vec = None
        raise Exception(
            "The start x and y columns and/or UID column "
            "are not present within the input file."
        )

    ds_objs_vec = gdal.OpenEx(vec_objs_file, gdal.OF_READONLY)
    if ds_objs_vec is None:
        raise Exception("Could not open '{}'".format(vec_objs_file))

    lyr_objs_vec = ds_objs_vec.GetLayerByName(vec_objs_lyr)
    if lyr_objs_vec is None:
        raise Exception("Could not find layer '{}'".format(vec_objs_lyr))

    ds_objs_sub_vec, lyr_objs_sub_vec = rsgislib.vectorutils.subsetEnvsVecLyrObj(
        lyr_objs_vec, vec_bbox
    )

    spat_ref = lyr_objs_vec.GetSpatialRef()

    out_driver = ogr.GetDriverByName(out_format)
    out_ds_obj = out_driver.CreateDataSource(out_vec_file)
    out_lyr_obj = out_ds_obj.CreateLayer(
        out_vec_lyr, spat_ref, geom_type=ogr.wkbLineString
    )
    uid_field_obj = ogr.FieldDefn("uid", ogr.OFTInteger)
    out_lyr_obj.CreateField(uid_field_obj)
    length_field = ogr.FieldDefn("len", ogr.OFTReal)
    out_lyr_obj.CreateField(length_field)
    feat_defn = out_lyr_obj.GetLayerDefn()

    geom_collect = ogr.Geometry(ogr.wkbGeometryCollection)
    n_obj_feats = lyr_objs_sub_vec.GetFeatureCount(True)
    geom_pbar = tqdm.tqdm(total=n_obj_feats, leave=True)
    in_obj_feat = lyr_objs_sub_vec.GetNextFeature()
    while in_obj_feat:
        geom = in_obj_feat.GetGeometryRef()
        if geom is not None:
            boundary = geom.Boundary()
            geom_collect.AddGeometry(boundary)
        in_obj_feat = lyr_objs_sub_vec.GetNextFeature()
        geom_pbar.update(1)
    geom_pbar.close()

    n_feats = lyr_line_vec.GetFeatureCount(True)
    pbar = tqdm.tqdm(total=n_feats, leave=True)
    open_transaction = False
    counter = 0
    in_feature = lyr_line_vec.GetNextFeature()
    while in_feature:
        if not open_transaction:
            out_lyr_obj.StartTransaction()
            open_transaction = True

        line_geom = in_feature.GetGeometryRef()
        if line_geom is not None:
            uid_str = in_feature.GetField(uid_field)
            start_pt_x = in_feature.GetField(start_x_field)
            start_pt_y = in_feature.GetField(start_y_field)
            start_pt = ogr.Geometry(ogr.wkbPoint)
            start_pt.AddPoint(start_pt_x, start_pt_y)

            inter_geom = geom_collect.Intersection(line_geom)

            if (inter_geom is not None) and (inter_geom.GetGeometryCount() > 0):
                min_dist_pt_x = 0.0
                min_dist_pt_y = 0.0
                min_dist = 0.0
                max_dist_pt_x = 0.0
                max_dist_pt_y = 0.0
                max_dist = 0.0
                c_pt = ogr.Geometry(ogr.wkbPoint)
                c_pt.AddPoint(0.0, 0.0)
                first_dist = True
                for i in range(inter_geom.GetGeometryCount()):
                    c_geom = inter_geom.GetGeometryRef(i)
                    pts = c_geom.GetPoints()
                    for pt in pts:
                        c_pt.SetPoint(0, pt[0], pt[1])
                        if first_dist:
                            min_dist = start_pt.Distance(c_pt)
                            min_dist_pt_x = pt[0]
                            min_dist_pt_y = pt[1]
                            max_dist = min_dist
                            max_dist_pt_x = min_dist_pt_x
                            max_dist_pt_y = min_dist_pt_y
                            first_dist = False
                        else:
                            pt_dist = start_pt.Distance(c_pt)
                            if pt_dist < min_dist:
                                min_dist = pt_dist
                                min_dist_pt_x = pt[0]
                                min_dist_pt_y = pt[1]
                            if pt_dist > max_dist:
                                max_dist = pt_dist
                                max_dist_pt_x = pt[0]
                                max_dist_pt_y = pt[1]
                out_line = ogr.Geometry(ogr.wkbLineString)
                out_line.AddPoint(min_dist_pt_x, min_dist_pt_y)
                out_line.AddPoint(max_dist_pt_x, max_dist_pt_y)
                out_feat = ogr.Feature(feat_defn)
                out_feat.SetGeometry(out_line)
                out_feat.SetField("uid", uid_str)
                start_pt.SetPoint(0, min_dist_pt_x, min_dist_pt_y)
                c_pt.SetPoint(0, max_dist_pt_x, max_dist_pt_y)
                dist = start_pt.Distance(c_pt)
                out_feat.SetField("len", dist)
                out_lyr_obj.CreateFeature(out_feat)
                out_feat = None

        if ((counter % 20000) == 0) and open_transaction:
            out_lyr_obj.CommitTransaction()
            open_transaction = False

        in_feature = lyr_line_vec.GetNextFeature()
        counter = counter + 1
        pbar.update(1)

    if open_transaction:
        out_lyr_obj.CommitTransaction()
        open_transaction = False
    pbar.close()
    out_lyr_obj.SyncToDisk()
    out_ds_obj = None
    ds_line_vec = None
    ds_objs_vec = None
    ds_objs_sub_vec = None


def scnd_line_intersection_range(
    vec_line_file,
    vec_line_lyr,
    vec_objs_file,
    vec_objs_lyr,
    out_vec_file,
    out_vec_lyr=None,
    start_x_field="start_x",
    start_y_field="start_y",
    uid_field="uid",
    out_format="GPKG",
    del_exist_vec=False,
):
    """
    A function which intersects a line with a set of polygons outputting the
    lines cut to their second point of intersection. Assume, first point of
    intersection would be entering the polygon and the second point of
    intersection would be leaving the polygon.

    :param vec_line_file: Input lines vector file path.
    :param vec_line_lyr: Input lines vector layer name.
    :param vec_objs_file: The vector file for the objects (expecting polygons)
                          to be intersected with.
    :param vec_objs_lyr: The vector layer for the objects (expecting polygons)
                         to be intersected with.
    :param out_vec_file: The output vector file path.
    :param out_vec_lyr: The output vector layer name
    :param start_x_field: The field name for the start point X coordinate
                          for the input lines.
    :param start_y_field: The field name for the start point Y coordinate
                          for the input lines.
    :param uid_field: The field name for the Unique ID (UID) of the input lines.
    :param out_format: The output file format of the vector file.
    :param del_exist_vec: remove output file if it exists.

    """
    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise Exception(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(out_vec_file)
            )

    if out_vec_lyr is None:
        out_vec_lyr = os.path.splitext(os.path.basename(out_vec_file))[0]

    gdal.UseExceptions()
    vec_bbox = rsgislib.vectorutils.get_vec_layer_extent(vec_line_file, vec_line_lyr)

    ds_line_vec = gdal.OpenEx(vec_line_file, gdal.OF_READONLY)
    if ds_line_vec is None:
        raise Exception("Could not open '{}'".format(vec_line_file))

    lyr_line_vec = ds_line_vec.GetLayerByName(vec_line_lyr)
    if lyr_line_vec is None:
        raise Exception("Could not find layer '{}'".format(vec_line_lyr))

    x_col_exists = False
    y_col_exists = False
    uid_col_exists = False
    lyr_line_defn = lyr_line_vec.GetLayerDefn()
    for i in range(lyr_line_defn.GetFieldCount()):
        if lyr_line_defn.GetFieldDefn(i).GetName() == start_x_field:
            x_col_exists = True
        if lyr_line_defn.GetFieldDefn(i).GetName() == start_y_field:
            y_col_exists = True
        if lyr_line_defn.GetFieldDefn(i).GetName() == uid_field:
            uid_col_exists = True
        if x_col_exists and y_col_exists and uid_col_exists:
            break

    if (not x_col_exists) or (not y_col_exists) or (not uid_col_exists):
        ds_line_vec = None
        raise Exception(
            "The start x and y columns and/or UID column are "
            "not present within the input file."
        )

    ds_objs_vec = gdal.OpenEx(vec_objs_file, gdal.OF_READONLY)
    if ds_objs_vec is None:
        raise Exception("Could not open '{}'".format(vec_objs_file))

    lyr_objs_vec = ds_objs_vec.GetLayerByName(vec_objs_lyr)
    if lyr_objs_vec is None:
        raise Exception("Could not find layer '{}'".format(vec_objs_lyr))

    ds_objs_sub_vec, lyr_objs_sub_vec = rsgislib.vectorutils.subsetEnvsVecLyrObj(
        lyr_objs_vec, vec_bbox
    )

    spat_ref = lyr_objs_vec.GetSpatialRef()

    out_driver = ogr.GetDriverByName(out_format)
    out_ds_obj = out_driver.CreateDataSource(out_vec_file)
    out_lyr_obj = out_ds_obj.CreateLayer(
        out_vec_lyr, spat_ref, geom_type=ogr.wkbLineString
    )
    uid_field_out_obj = ogr.FieldDefn("uid", ogr.OFTInteger)
    out_lyr_obj.CreateField(uid_field_out_obj)
    start_x_out_field = ogr.FieldDefn("start_x", ogr.OFTReal)
    out_lyr_obj.CreateField(start_x_out_field)
    start_y_out_field = ogr.FieldDefn("start_y", ogr.OFTReal)
    out_lyr_obj.CreateField(start_y_out_field)
    end_x_out_field = ogr.FieldDefn("end_x", ogr.OFTReal)
    out_lyr_obj.CreateField(end_x_out_field)
    end_y_out_field = ogr.FieldDefn("end_y", ogr.OFTReal)
    out_lyr_obj.CreateField(end_y_out_field)
    length_field = ogr.FieldDefn("len", ogr.OFTReal)
    out_lyr_obj.CreateField(length_field)
    feat_defn = out_lyr_obj.GetLayerDefn()

    geom_collect = ogr.Geometry(ogr.wkbGeometryCollection)
    n_obj_feats = lyr_objs_sub_vec.GetFeatureCount(True)
    geom_pbar = tqdm.tqdm(total=n_obj_feats, leave=True)
    in_obj_feat = lyr_objs_sub_vec.GetNextFeature()
    while in_obj_feat:
        geom = in_obj_feat.GetGeometryRef()
        if geom is not None:
            boundary = geom.Boundary()
            geom_collect.AddGeometry(boundary)
        in_obj_feat = lyr_objs_sub_vec.GetNextFeature()
        geom_pbar.update(1)
    geom_pbar.close()

    n_feats = lyr_line_vec.GetFeatureCount(True)
    pbar = tqdm.tqdm(total=n_feats, leave=True)
    open_transaction = False
    counter = 0
    in_feature = lyr_line_vec.GetNextFeature()
    while in_feature:
        if not open_transaction:
            out_lyr_obj.StartTransaction()
            open_transaction = True

        line_geom = in_feature.GetGeometryRef()
        if line_geom is not None:
            uid_str = in_feature.GetField(uid_field)
            start_pt_x = in_feature.GetField(start_x_field)
            start_pt_y = in_feature.GetField(start_y_field)
            start_pt = ogr.Geometry(ogr.wkbPoint)
            start_pt.AddPoint(start_pt_x, start_pt_y)

            inter_geom = geom_collect.Intersection(line_geom)

            if (inter_geom is not None) and (inter_geom.GetGeometryCount() > 0):
                min_dist_pt_x = 0.0
                min_dist_pt_y = 0.0
                min_dist = 0.0
                sec_dist_pt_x = 0.0
                sec_dist_pt_y = 0.0
                sec_dist = 0.0
                c_pt = ogr.Geometry(ogr.wkbPoint)
                c_pt.AddPoint(0.0, 0.0)
                first_dist = True
                first_sec = True
                for i in range(inter_geom.GetGeometryCount()):
                    c_geom = inter_geom.GetGeometryRef(i)
                    pts = c_geom.GetPoints()
                    for pt in pts:
                        c_pt.SetPoint(0, pt[0], pt[1])
                        if first_dist:
                            min_dist = start_pt.Distance(c_pt)
                            min_dist_pt_x = pt[0]
                            min_dist_pt_y = pt[1]
                            first_dist = False
                        elif first_sec:
                            pt_dist = start_pt.Distance(c_pt)
                            if pt_dist < min_dist:
                                sec_dist = min_dist
                                sec_dist_pt_x = min_dist_pt_x
                                sec_dist_pt_y = min_dist_pt_y
                                min_dist = pt_dist
                                min_dist_pt_x = pt[0]
                                min_dist_pt_y = pt[1]
                            else:
                                sec_dist = pt_dist
                                sec_dist_pt_x = pt[0]
                                sec_dist_pt_y = pt[1]
                            first_sec = False
                        else:
                            pt_dist = start_pt.Distance(c_pt)
                            if pt_dist < min_dist:
                                sec_dist = min_dist
                                sec_dist_pt_x = min_dist_pt_x
                                sec_dist_pt_y = min_dist_pt_y
                                min_dist = pt_dist
                                min_dist_pt_x = pt[0]
                                min_dist_pt_y = pt[1]
                            elif pt_dist < sec_dist:
                                sec_dist = pt_dist
                                sec_dist_pt_x = pt[0]
                                sec_dist_pt_y = pt[1]

                out_line = ogr.Geometry(ogr.wkbLineString)
                out_line.AddPoint(start_pt_x, start_pt_y)
                out_line.AddPoint(sec_dist_pt_x, sec_dist_pt_y)
                out_feat = ogr.Feature(feat_defn)
                out_feat.SetGeometry(out_line)
                out_feat.SetField("uid", uid_str)
                c_pt.SetPoint(0, sec_dist_pt_x, sec_dist_pt_y)
                dist = start_pt.Distance(c_pt)
                out_feat.SetField("len", dist)
                out_feat.SetField("start_x", start_pt_x)
                out_feat.SetField("start_y", start_pt_y)
                out_feat.SetField("end_x", sec_dist_pt_x)
                out_feat.SetField("end_y", sec_dist_pt_y)
                out_lyr_obj.CreateFeature(out_feat)
                out_feat = None

        if ((counter % 20000) == 0) and open_transaction:
            out_lyr_obj.CommitTransaction()
            open_transaction = False

        in_feature = lyr_line_vec.GetNextFeature()
        counter = counter + 1
        pbar.update(1)

    if open_transaction:
        out_lyr_obj.CommitTransaction()
        open_transaction = False
    pbar.close()
    out_lyr_obj.SyncToDisk()
    out_ds_obj = None
    ds_line_vec = None
    ds_objs_vec = None
    ds_objs_sub_vec = None


def create_rtree_index(vec_file, vec_lyr):
    """
    A function which creates a spatial index using the rtree package for the
    inputted vector file/layer.

    :param vec_file: Input vector file to be processed.
    :param vec_lyr: The layer within the vector file for which the index is to be built.

    """
    import rtree

    vec_file_obj = gdal.OpenEx(vec_file, gdal.OF_READONLY)
    if vec_file_obj is None:
        raise Exception("Could not open '{}'".format(vec_file))

    vec_lyr_obj = vec_file_obj.GetLayerByName(vec_lyr)
    if vec_lyr_obj is None:
        raise Exception("Could not find layer '{}'".format(vec_lyr))

    idx_obj = rtree.index.Index(interleaved=False)
    geom_lst = list()

    n_feats = vec_lyr_obj.GetFeatureCount(True)
    n_geom = 0
    pbar = tqdm.tqdm(total=n_feats)
    vec_lyr_obj.ResetReading()
    feat = vec_lyr_obj.GetNextFeature()
    while feat is not None:
        geom_obj = feat.GetGeometryRef()
        if geom_obj is not None:
            xmin, xmax, ymin, ymax = geom_obj.GetEnvelope()
            geom_lst.append(geom_obj.Clone())
            idx_obj.insert(n_geom, (xmin, xmax, ymin, ymax))
            n_geom = n_geom + 1
        pbar.update(1)
        feat = vec_lyr_obj.GetNextFeature()
    vec_file_obj = None
    return idx_obj, geom_lst


def bbox_intersects_index(rt_idx, geom_lst, bbox):
    """
    A function which tests for intersection between the geometries and the bounding box
    using a spatial index.

    :param rt_idx: the rtree spatial index object (created using the
                   create_rtree_index function)
    :param geom_lst: the list of geometries as referenced in the index (created
                     using the create_rtree_index function)
    :param bbox: the bounding box (xMin, xMax, yMin, yMax). Same projection as
                  geometries in the index.
    :return: True there is an intersection. False there is not an intersection.

    """
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(bbox[0], bbox[3])
    ring.AddPoint(bbox[1], bbox[3])
    ring.AddPoint(bbox[1], bbox[2])
    ring.AddPoint(bbox[0], bbox[2])
    ring.AddPoint(bbox[0], bbox[3])
    # Create polygon.
    poly_bbox = ogr.Geometry(ogr.wkbPolygon)
    poly_bbox.AddGeometry(ring)

    bbox_intersects = False

    for geom_idx in list(rt_idx.intersection(bbox)):
        print(geom_idx)
        geom_obj = geom_lst[geom_idx]
        if poly_bbox.Intersects(geom_obj):
            bbox_intersects = True
            break
    return bbox_intersects


def calc_poly_centroids(vec_file, vec_lyr, out_format, out_vec_file, out_vec_lyr):
    """
    Create a vector layer of the polygon centroids.

    :param vec_file: input vector file
    :param vec_lyr: input vector layer within the input file.
    :param out_format: the format driver for the output vector file (e.g., GPKG).
    :param out_vec_file: output file path for the vector.
    :param out_vec_lyr: output vector layer name.

    """
    vecDS = gdal.OpenEx(vec_file, gdal.OF_VECTOR)
    if vecDS is None:
        raise Exception("Could not open '{}'".format(vec_file))

    vec_lyr_obj = vecDS.GetLayerByName(vec_lyr)
    if vec_lyr_obj is None:
        raise Exception("Could not open layer '{}'".format(vec_lyr))
    lyr_spat_ref = vec_lyr_obj.GetSpatialRef()

    out_driver = ogr.GetDriverByName(out_format)
    result_ds = out_driver.CreateDataSource(out_vec_file)
    if result_ds is None:
        raise Exception("Could not open '{}'".format(out_vec_file))

    result_lyr = result_ds.CreateLayer(
        out_vec_lyr, lyr_spat_ref, geom_type=ogr.wkbPoint
    )
    if result_lyr is None:
        raise Exception("Could not open layer '{}'".format(out_vec_lyr))

    featDefn = result_lyr.GetLayerDefn()

    openTransaction = False
    vec_lyr_obj.ResetReading()
    n_feats = vec_lyr_obj.GetFeatureCount(True)
    print(n_feats)
    counter = 0
    pbar = tqdm.tqdm(total=n_feats)
    vec_lyr_obj.ResetReading()
    feat = vec_lyr_obj.GetNextFeature()
    while feat is not None:
        if not openTransaction:
            result_lyr.StartTransaction()
            openTransaction = True

        pt = feat.GetGeometryRef().Centroid()
        outFeat = ogr.Feature(featDefn)
        outFeat.SetGeometry(pt)
        result_lyr.CreateFeature(outFeat)

        if ((counter % 20000) == 0) and openTransaction:
            result_lyr.CommitTransaction()
            openTransaction = False

        feat = vec_lyr_obj.GetNextFeature()
        counter = counter + 1
        pbar.update(1)

    if openTransaction:
        result_lyr.CommitTransaction()
        openTransaction = False
    result_lyr.SyncToDisk()
    pbar.close()

    vecDS = None
    result_ds = None


def vec_lyr_intersection_gp(
    vec_file,
    vec_lyr,
    vec_over_file,
    vec_over_lyr,
    out_vec_file,
    out_vec_lyr=None,
    out_format="GPKG",
    del_exist_vec=False,
):
    """
    A function which performs an intersection between the vector layer and the
    overlain vector using Geopandas.

    :param vec_file: Input vector file path.
    :param vec_lyr: Input vector layer name.
    :param vec_over_file: The vector file overlained on the input vector file.
    :param vec_over_lyr: The vector layer overlained on the input vector file.
    :param out_vec_file: The output vector file path.
    :param out_vec_lyr: The output vector layer name.
    :param out_format: The output file format of the vector file.
    :param del_exist_vec: remove output file if it exists.
    """
    import os
    import geopandas

    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise Exception(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(out_vec_file)
            )

    if out_vec_lyr is None:
        out_vec_lyr = os.path.splitext(os.path.basename(out_vec_file))[0]

    data_gdf = geopandas.read_file(vec_file, layer=vec_lyr)
    over_data_gdf = geopandas.read_file(vec_over_file, layer=vec_over_lyr)
    # Perform Intersection
    data_inter_gdf = geopandas.overlay(data_gdf, over_data_gdf, how="intersection")

    if out_format == "GPKG":
        if out_vec_lyr is None:
            raise Exception(
                "If output format is GPKG then an output layer is required."
            )
        data_inter_gdf.to_file(out_vec_file, layer=out_vec_lyr, driver=out_format)
    else:
        data_inter_gdf.to_file(out_vec_file, driver=out_format)


def vec_lyr_difference_gp(
    vec_file,
    vec_lyr,
    vec_over_file,
    vec_over_lyr,
    out_vec_file,
    out_vec_lyr=None,
    out_format="GPKG",
    del_exist_vec=False,
):
    """
    A function which performs a difference between the vector layer and the
    overlain vector using Geopandas.

    :param vec_file: Input vector file path.
    :param vec_lyr: Input vector layer name.
    :param vec_over_file: The vector file overlained on the input vector file.
    :param vec_over_lyr: The vector layer overlained on the input vector file.
    :param out_vec_file: The output vector file path.
    :param out_vec_lyr: The output vector layer name.
    :param out_format: The output file format of the vector file.
    :param del_exist_vec: remove output file if it exists.
    """
    import os
    import geopandas

    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise Exception(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(out_vec_file)
            )

    if out_vec_lyr is None:
        out_vec_lyr = os.path.splitext(os.path.basename(out_vec_file))[0]

    data_gdf = geopandas.read_file(vec_file, layer=vec_lyr)
    over_data_gdf = geopandas.read_file(vec_over_file, layer=vec_over_lyr)
    # Perform Difference
    data_inter_gdf = geopandas.overlay(data_gdf, over_data_gdf, how="difference")

    if out_format == "GPKG":
        if out_vec_lyr is None:
            raise Exception(
                "If output format is GPKG then an output layer is required."
            )
        data_inter_gdf.to_file(out_vec_file, layer=out_vec_lyr, driver=out_format)
    else:
        data_inter_gdf.to_file(out_vec_file, driver=out_format)


def vec_lyr_sym_difference_gp(
    vec_file,
    vec_lyr,
    vec_over_file,
    vec_over_lyr,
    out_vec_file,
    out_vec_lyr=None,
    out_format="GPKG",
    del_exist_vec=False,
):
    """
    A function which performs a symmetric difference between the vector layer
    and the overlain vector using Geopandas.

    :param vec_file: Input vector file path.
    :param vec_lyr: Input vector layer name.
    :param vec_over_file: The vector file overlained on the input vector file.
    :param vec_over_lyr: The vector layer overlained on the input vector file.
    :param out_vec_file: The output vector file path.
    :param out_vec_lyr: The output vector layer name.
    :param out_format: The output file format of the vector file.
    :param del_exist_vec: remove output file if it exists.
    """
    import os
    import geopandas

    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise Exception(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(out_vec_file)
            )

    if out_vec_lyr is None:
        out_vec_lyr = os.path.splitext(os.path.basename(out_vec_file))[0]

    data_gdf = geopandas.read_file(vec_file, layer=vec_lyr)
    over_data_gdf = geopandas.read_file(vec_over_file, layer=vec_over_lyr)
    # Perform symmetric difference
    data_inter_gdf = geopandas.overlay(
        data_gdf, over_data_gdf, how="symmetric_difference"
    )

    if out_format == "GPKG":
        if out_vec_lyr is None:
            raise Exception(
                "If output format is GPKG then an output layer is required."
            )
        data_inter_gdf.to_file(out_vec_file, layer=out_vec_lyr, driver=out_format)
    else:
        data_inter_gdf.to_file(out_vec_file, driver=out_format)


def vec_lyr_identity_gp(
    vec_file,
    vec_lyr,
    vec_over_file,
    vec_over_lyr,
    out_vec_file,
    out_vec_lyr=None,
    out_format="GPKG",
    del_exist_vec=False,
):
    """
    A function which performs a identity between the vector layer and the
    overlain vector using Geopandas.

    The result consists of the surface of vec_file, but with the geometries obtained
    from overlaying vec_file with vec_over_file.

    :param vec_file: Input vector file path.
    :param vec_lyr: Input vector layer name.
    :param vec_over_file: The vector file overlained on the input vector file.
    :param vec_over_lyr: The vector layer overlained on the input vector file.
    :param out_vec_file: The output vector file path.
    :param out_vec_lyr: The output vector layer name.
    :param out_format: The output file format of the vector file.
    :param del_exist_vec: remove output file if it exists.
    """
    import os
    import geopandas

    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise Exception(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(out_vec_file)
            )

    if out_vec_lyr is None:
        out_vec_lyr = os.path.splitext(os.path.basename(out_vec_file))[0]

    data_gdf = geopandas.read_file(vec_file, layer=vec_lyr)
    over_data_gdf = geopandas.read_file(vec_over_file, layer=vec_over_lyr)
    # Perform identity
    data_inter_gdf = geopandas.overlay(data_gdf, over_data_gdf, how="identity")

    if out_format == "GPKG":
        if out_vec_lyr is None:
            raise Exception(
                "If output format is GPKG then an output layer is required."
            )
        data_inter_gdf.to_file(out_vec_file, layer=out_vec_lyr, driver=out_format)
    else:
        data_inter_gdf.to_file(out_vec_file, driver=out_format)


def vec_lyr_union_gp(
    vec_file,
    vec_lyr,
    vec_over_file,
    vec_over_lyr,
    out_vec_file,
    out_vec_lyr=None,
    out_format="GPKG",
    del_exist_vec=False,
):
    """
    A function which performs a union between the vector layer and the
    overlain vector using Geopandas.

    :param vec_file: Input vector file path.
    :param vec_lyr: Input vector layer name.
    :param vec_over_file: The vector file overlained on the input vector file.
    :param vec_over_lyr: The vector layer overlained on the input vector file.
    :param out_vec_file: The output vector file path.
    :param out_vec_lyr: The output vector layer name.
    :param out_format: The output file format of the vector file.
    :param del_exist_vec: remove output file if it exists.
    """
    import os
    import geopandas

    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise Exception(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(out_vec_file)
            )

    if out_vec_lyr is None:
        out_vec_lyr = os.path.splitext(os.path.basename(out_vec_file))[0]

    data_gdf = geopandas.read_file(vec_file, layer=vec_lyr)
    over_data_gdf = geopandas.read_file(vec_over_file, layer=vec_over_lyr)
    # Perform union
    data_inter_gdf = geopandas.overlay(data_gdf, over_data_gdf, how="union")

    if out_format == "GPKG":
        if out_vec_lyr is None:
            raise Exception(
                "If output format is GPKG then an output layer is required."
            )
        data_inter_gdf.to_file(out_vec_file, layer=out_vec_lyr, driver=out_format)
    else:
        data_inter_gdf.to_file(out_vec_file, driver=out_format)


def get_vec_lyr_as_pts(in_vec_file, in_vec_lyr):
    """
    Get a list of points from the vectors within an input file.

    :param in_vec_file: Input vector file
    :param in_vec_lyr: Input vector layer name
    :return: returns a list of points.

    """
    from osgeo import gdal
    import tqdm

    gdal.UseExceptions()
    vec_ds_obj = gdal.OpenEx(in_vec_file, gdal.OF_VECTOR)
    vec_lyr_obj = vec_ds_obj.GetLayer(in_vec_lyr)

    pts_lst = list()
    n_feats = vec_lyr_obj.GetFeatureCount(True)
    pbar = tqdm.tqdm(total=n_feats)
    counter = 0
    in_feature = vec_lyr_obj.GetNextFeature()
    while in_feature:
        geom = in_feature.GetGeometryRef()
        if geom is not None:
            get_geom_pts(geom, pts_lst)
        in_feature = vec_lyr_obj.GetNextFeature()
        counter = counter + 1
        pbar.update(1)
    pbar.close()
    return pts_lst


def create_alpha_shape(
    in_vec_file,
    in_vec_lyr,
    out_vec_file,
    out_vec_lyr,
    out_format="GPKG",
    alpha_val=None,
    alpha_vals=None,
    max_iter=10000,
    del_exist_vec=False,
):
    """
    Function which calculate an alpha shape for a set of vector features
    (which are converted to points).

    For this function to work you need the alphashapes module installed:
    https://alphashape.readthedocs.io
    https://github.com/bellockk/alphashape

    :param in_vec_file: the input vector file.
    :param in_vec_lyr: the input vector layer name
    :param out_vec_file: the output vector file.
    :param out_vec_lyr: the name of the output vector layer (if None then
                        the same as the input).
    :param out_format: the output vector file format (e.g., GPKG)
    :param alpha_val: The alpha value to create the the alpha shape
                      polygon. If None then a value will be automatically
                      calculate but warning this can a significant amount
                      of time (i.e., hours!!)
    :param alpha_vals: Alternatively, a list of alpha values can be provided
                       (e.g., [75, 50, 25, 5, 2]) where first to produce a valid
                       result will be outputted. i.e., the order you provide the alpha
                       values will be the order they are tested. If None then the
                       alpha_val parameter will be used.
    :param max_iter: The maximum number of iterations for automatically selecting
                     the alpha value. Note if the number iteration is not sufficient
                     to find an optimum value then no value is returned.
    :param del_exist_vec: remove output file if it exists.
    :return: (vec_output, alpha_val); vec_output is a boolean True an output
                                      produced; False no output, alpha_val - the
                                      alpha value used for the analysis. If a single
                                      value was inputted then the same value will
                                      be outputted.

    """
    import alphashape
    from osgeo import ogr
    from osgeo import gdal
    import os

    gdal.UseExceptions()

    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise Exception(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(out_vec_file)
            )

    def _rescale_polygon(in_poly, min_x, min_y, ran_x, ran_y):
        ext_ring = ogr.Geometry(ogr.wkbLinearRing)
        for pt in in_poly.exterior.coords:
            ext_ring.AddPoint(((pt[0] * ran_x) + min_x), ((pt[1] * ran_y) + min_y))
        n_poly = ogr.Geometry(ogr.wkbPolygon)
        n_poly.AddGeometry(ext_ring)

        for int_ring in in_poly.interiors:
            n_int_ring = ogr.Geometry(ogr.wkbLinearRing)
            for pt in int_ring.coords:
                n_int_ring.AddPoint(
                    ((pt[0] * ran_x) + min_x), ((pt[1] * ran_y) + min_y)
                )
            n_poly.AddGeometry(n_int_ring)
        return n_poly

    pts = get_vec_lyr_as_pts(in_vec_file, in_vec_lyr)
    min_x = 0.0
    min_y = 0.0
    max_x = 0.0
    max_y = 0.0
    first = True
    for pt in pts:
        if first:
            min_x = pt[0]
            min_y = pt[1]
            max_x = pt[0]
            max_y = pt[1]
            first = False
        else:
            if pt[0] < min_x:
                min_x = pt[0]
            if pt[1] < min_y:
                min_y = pt[1]
            if pt[0] > max_x:
                max_x = pt[0]
            if pt[1] > max_y:
                max_y = pt[1]

    print("Min: {}, {}".format(min_x, min_y))
    print("Max: {}, {}".format(max_x, max_y))

    ran_x = max_x - min_x
    ran_y = max_y - min_y
    print("Range: {}, {}".format(ran_x, ran_y))

    norm_pts = list()
    for pt in pts:
        norm_x = (pt[0] - min_x) / ran_x
        norm_y = (pt[1] - min_y) / ran_y
        norm_pts.append((norm_x, norm_y))

    if alpha_vals is not None:
        for alpha_test_val in alpha_vals:
            print("Trying Alpha: {}".format(alpha_test_val))
            alpha_shape = alphashape.alphashape(norm_pts, alpha=alpha_test_val)
            if (
                alpha_shape.geom_type == "MultiPolygon"
                or alpha_shape.geom_type == "Polygon"
            ):
                alpha_val = alpha_test_val
                break
        print("Final Alpha: {}".format(alpha_val))
    else:
        if alpha_val is None:
            alpha_val = alphashape.optimizealpha(norm_pts, max_iterations=max_iter)

        print("Alpha: {}".format(alpha_val))
        alpha_shape = alphashape.alphashape(norm_pts, alpha=alpha_val)

    ogr_geom_type = ogr.wkbPolygon
    if alpha_shape.geom_type == "MultiPolygon":
        ogr_geom_type = ogr.wkbMultiPolygon
        out_alpha_shape = ogr.Geometry(ogr.wkbMultiPolygon)
        for poly in alpha_shape:
            out_alpha_shape.AddGeometry(
                _rescale_polygon(poly, min_x, min_y, ran_x, ran_y)
            )
    elif alpha_shape.geom_type == "Polygon":
        ogr_geom_type = ogr.wkbPolygon
        out_alpha_shape = _rescale_polygon(alpha_shape, min_x, min_y, ran_x, ran_y)
    else:
        out_alpha_shape = None
        print("No output, did not create an output polygon or multipolygon...")

    vec_output = False
    if out_alpha_shape is not None:
        vecDS = gdal.OpenEx(in_vec_file, gdal.OF_VECTOR)
        if vecDS is None:
            raise Exception("Could not open '{}'".format(in_vec_file))
        vec_lyr_obj = vecDS.GetLayerByName(in_vec_lyr)
        if vec_lyr_obj is None:
            raise Exception("Could not open layer '{}'".format(in_vec_lyr))
        lyr_spat_ref = vec_lyr_obj.GetSpatialRef()
        vecDS = None

        out_driver = ogr.GetDriverByName(out_format)
        result_ds = out_driver.CreateDataSource(out_vec_file)
        if result_ds is None:
            raise Exception("Could not open '{}'".format(out_vec_file))

        result_lyr = result_ds.CreateLayer(
            out_vec_lyr, lyr_spat_ref, geom_type=ogr_geom_type
        )
        if result_lyr is None:
            raise Exception("Could not open layer '{}'".format(out_vec_lyr))

        # Get the output Layer's Feature Definition
        featureDefn = result_lyr.GetLayerDefn()
        outFeature = ogr.Feature(featureDefn)
        outFeature.SetGeometry(out_alpha_shape)
        result_lyr.CreateFeature(outFeature)
        outFeature = None
        result_ds = None
        vec_output = True

    return vec_output, alpha_val


def convert_multi_geoms_to_single(
    vec_file, vec_lyr, out_format, out_vec_file, out_vec_lyr, del_exist_vec=False
):
    """
    A convert any multiple geometries into single geometries.

    :param vec_file: input vector file
    :param vec_lyr: input vector layer within the input file.
    :param out_format: the format driver for the output vector
                       file (e.g., GPKG, ESRI Shapefile).
    :param out_vec_file: output file path for the vector.
    :param out_vec_lyr: output vector layer name.
    :param del_exist_vec: remove output file if it exists.

    """
    import rsgislib.vectorutils
    from osgeo import gdal
    from osgeo import ogr
    import tqdm

    gdal.UseExceptions()

    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise Exception(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(out_vec_file)
            )

    vecDS = gdal.OpenEx(vec_file, gdal.OF_VECTOR)
    if vecDS is None:
        raise Exception("Could not open '{}'".format(vec_file))

    vec_lyr_obj = vecDS.GetLayerByName(vec_lyr)
    if vec_lyr_obj is None:
        raise Exception("Could not open layer '{}'".format(vec_lyr))
    lyr_spat_ref = vec_lyr_obj.GetSpatialRef()
    geom_type = vec_lyr_obj.GetGeomType()
    if geom_type == ogr.wkbMultiPoint:
        geom_type = ogr.wkbPoint
        print("Changing to Point Type from Multi-Point")
    elif geom_type == ogr.wkbMultiLineString:
        geom_type = ogr.wkbLineString
        print("Changing to Line Type from Multi-Line")
    elif geom_type == ogr.wkbMultiPolygon:
        geom_type = ogr.wkbPolygon
        print("Changing to Polygon Type from Multi-Polygon")

    out_driver = ogr.GetDriverByName(out_format)
    result_ds = out_driver.CreateDataSource(out_vec_file)
    if result_ds is None:
        raise Exception("Could not open '{}'".format(out_vec_file))

    result_lyr = result_ds.CreateLayer(out_vec_lyr, lyr_spat_ref, geom_type=geom_type)
    if result_lyr is None:
        raise Exception("Could not open layer '{}'".format(out_vec_lyr))

    featDefn = result_lyr.GetLayerDefn()

    openTransaction = False
    vec_lyr_obj.ResetReading()
    n_feats = vec_lyr_obj.GetFeatureCount(True)
    counter = 0
    pbar = tqdm.tqdm(total=n_feats)
    vec_lyr_obj.ResetReading()
    feat = vec_lyr_obj.GetNextFeature()
    while feat is not None:
        if not openTransaction:
            result_lyr.StartTransaction()
            openTransaction = True

        geom_ref = feat.GetGeometryRef()

        if geom_ref.GetGeometryName().lower() == "multipolygon":
            for i in range(0, geom_ref.GetGeometryCount()):
                g = geom_ref.GetGeometryRef(i)
                outFeat = ogr.Feature(featDefn)
                outFeat.SetGeometry(g)
                result_lyr.CreateFeature(outFeat)
        elif geom_ref.GetGeometryName().lower() == "multilinestring":
            for i in range(0, geom_ref.GetGeometryCount()):
                g = geom_ref.GetGeometryRef(i)
                outFeat = ogr.Feature(featDefn)
                outFeat.SetGeometry(g)
                result_lyr.CreateFeature(outFeat)
        elif geom_ref.GetGeometryName().lower() == "multipoint":
            for i in range(0, geom_ref.GetGeometryCount()):
                g = geom_ref.GetGeometryRef(i)
                outFeat = ogr.Feature(featDefn)
                outFeat.SetGeometry(g)
                result_lyr.CreateFeature(outFeat)
        elif geom_ref.GetGeometryName().lower() == "geometrycollection":
            for i in range(0, geom_ref.GetGeometryCount()):
                g = geom_ref.GetGeometryRef(i)
                outFeat = ogr.Feature(featDefn)
                outFeat.SetGeometry(g)
                result_lyr.CreateFeature(outFeat)
        else:
            outFeat = ogr.Feature(featDefn)
            outFeat.SetGeometry(geom_ref)
            result_lyr.CreateFeature(outFeat)

        if ((counter % 20000) == 0) and openTransaction:
            result_lyr.CommitTransaction()
            openTransaction = False

        feat = vec_lyr_obj.GetNextFeature()
        counter += 1
        pbar.update(1)

    if openTransaction:
        result_lyr.CommitTransaction()
        openTransaction = False
    result_lyr.SyncToDisk()
    pbar.close()

    vecDS = None
    result_ds = None


def simplify_geometries(
    vec_file,
    vec_lyr,
    tolerance,
    out_format,
    out_vec_file,
    out_vec_lyr,
    del_exist_vec=False,
):
    """
    Create a simplified version of the input

    :param vec_file: input vector file
    :param vec_lyr: input vector layer within the input file.
    :param tolerance: simplification tolerance
    :param out_format: the format driver for the output vector
                       file (e.g., GPKG, ESRI Shapefile).
    :param out_vec_file: output file path for the vector.
    :param out_vec_lyr: output vector layer name.
    :param del_exist_vec: remove output file if it exists.
    """
    from osgeo import gdal
    from osgeo import ogr
    import tqdm

    gdal.UseExceptions()

    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise Exception(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(out_vec_file)
            )

    vecDS = gdal.OpenEx(vec_file, gdal.OF_VECTOR)
    if vecDS is None:
        raise Exception("Could not open '{}'".format(vec_file))

    vec_lyr_obj = vecDS.GetLayerByName(vec_lyr)
    if vec_lyr_obj is None:
        raise Exception("Could not open layer '{}'".format(vec_lyr))
    lyr_spat_ref = vec_lyr_obj.GetSpatialRef()
    geom_type = vec_lyr_obj.GetGeomType()

    out_driver = ogr.GetDriverByName(out_format)
    result_ds = out_driver.CreateDataSource(out_vec_file)
    if result_ds is None:
        raise Exception("Could not open '{}'".format(out_vec_file))

    result_lyr = result_ds.CreateLayer(out_vec_lyr, lyr_spat_ref, geom_type=geom_type)
    if result_lyr is None:
        raise Exception("Could not open layer '{}'".format(out_vec_lyr))

    featDefn = result_lyr.GetLayerDefn()

    openTransaction = False
    vec_lyr_obj.ResetReading()
    n_feats = vec_lyr_obj.GetFeatureCount(True)
    counter = 0
    pbar = tqdm.tqdm(total=n_feats)
    vec_lyr_obj.ResetReading()
    feat = vec_lyr_obj.GetNextFeature()
    while feat is not None:
        if not openTransaction:
            result_lyr.StartTransaction()
            openTransaction = True

        geom = feat.GetGeometryRef().Simplify(tolerance)
        outFeat = ogr.Feature(featDefn)
        outFeat.SetGeometry(geom)
        result_lyr.CreateFeature(outFeat)

        if ((counter % 20000) == 0) and openTransaction:
            result_lyr.CommitTransaction()
            openTransaction = False

        feat = vec_lyr_obj.GetNextFeature()
        counter = counter + 1
        pbar.update(1)

    if openTransaction:
        result_lyr.CommitTransaction()
        openTransaction = False
    result_lyr.SyncToDisk()
    pbar.close()

    vecDS = None
    result_ds = None


def delete_polygon_holes(
    vec_file,
    vec_lyr,
    out_format,
    out_vec_file,
    out_vec_lyr,
    area_thres=None,
    del_exist_vec=False,
):
    """
    Delete holes from the input polygons in below the area threshold.

    :param vec_file: input vector file
    :param vec_lyr: input vector layer within the input file.
    :param out_format: the format driver for the output vector
                       file (e.g., GPKG, ESRI Shapefile).
    :param out_vec_file: output file path for the vector.
    :param out_vec_lyr: output vector layer name.
    :param area_thres: threshold below which holes are removed. If
                       threshold is None then all holes are removed.
    :param del_exist_vec: remove output file if it exists.
    """
    from osgeo import gdal
    from osgeo import ogr
    import tqdm

    gdal.UseExceptions()

    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise Exception(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(out_vec_file)
            )

    def _remove_holes_polygon(polygon, area_thres=None):
        if polygon.GetGeometryName().lower() != "polygon":
            raise Exception("Can only remove holes from polygon geometry.")
        if polygon.GetGeometryCount() == 1:
            return polygon

        if area_thres is None:
            outer_ring = polygon.GetGeometryRef(0)
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(outer_ring)
            return poly
        else:
            outer_ring = polygon.GetGeometryRef(0)
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(outer_ring)
            for i in range(polygon.GetGeometryCount()):
                if i > 0:
                    c_ring = polygon.GetGeometryRef(i)
                    tmp_poly = ogr.Geometry(ogr.wkbPolygon)
                    tmp_poly.AddGeometry(c_ring)
                    if tmp_poly.Area() > area_thres:
                        poly.AddGeometry(c_ring)
            return poly

    vecDS = gdal.OpenEx(vec_file, gdal.OF_VECTOR)
    if vecDS is None:
        raise Exception("Could not open '{}'".format(vec_file))

    vec_lyr_obj = vecDS.GetLayerByName(vec_lyr)
    if vec_lyr_obj is None:
        raise Exception("Could not open layer '{}'".format(vec_lyr))
    lyr_spat_ref = vec_lyr_obj.GetSpatialRef()
    geom_type = vec_lyr_obj.GetGeomType()

    out_driver = ogr.GetDriverByName(out_format)
    result_ds = out_driver.CreateDataSource(out_vec_file)
    if result_ds is None:
        raise Exception("Could not open '{}'".format(out_vec_file))

    result_lyr = result_ds.CreateLayer(out_vec_lyr, lyr_spat_ref, geom_type=geom_type)
    if result_lyr is None:
        raise Exception("Could not open layer '{}'".format(out_vec_lyr))

    featDefn = result_lyr.GetLayerDefn()

    openTransaction = False
    vec_lyr_obj.ResetReading()
    n_feats = vec_lyr_obj.GetFeatureCount(True)
    counter = 0
    pbar = tqdm.tqdm(total=n_feats)
    vec_lyr_obj.ResetReading()
    feat = vec_lyr_obj.GetNextFeature()
    while feat is not None:
        if not openTransaction:
            result_lyr.StartTransaction()
            openTransaction = True

        geom_ref = feat.GetGeometryRef()
        if geom_ref.GetGeometryName().lower() == "multipolygon":
            out_geom = ogr.Geometry(ogr.wkbMultiPolygon)
            for i in range(0, geom_ref.GetGeometryCount()):
                g = geom_ref.GetGeometryRef(i)
                out_geom.AddGeometry(_remove_holes_polygon(g, area_thres))
        elif geom_ref.GetGeometryName().lower() == "polygon":
            out_geom = _remove_holes_polygon(geom_ref, area_thres)

        if out_geom is not None:
            outFeat = ogr.Feature(featDefn)
            outFeat.SetGeometry(out_geom)
            result_lyr.CreateFeature(outFeat)

        if ((counter % 20000) == 0) and openTransaction:
            result_lyr.CommitTransaction()
            openTransaction = False

        feat = vec_lyr_obj.GetNextFeature()
        counter = counter + 1
        pbar.update(1)

    if openTransaction:
        result_lyr.CommitTransaction()
        openTransaction = False
    result_lyr.SyncToDisk()
    pbar.close()

    vecDS = None
    result_ds = None


def get_poly_hole_area(vec_file, vec_lyr):
    """
    Get an array of the areas of the polygon holes.

    :param vec_file: input vector file
    :param vec_lyr: input vector layer within the input file.
    :returns: A list of areas.
    """
    from osgeo import gdal
    from osgeo import ogr
    import tqdm

    gdal.UseExceptions()

    def _calc_hole_area(polygon):
        if polygon.GetGeometryName().lower() != "polygon":
            raise Exception("Can only remove holes from polygon geometry.")
        if polygon.GetGeometryCount() == 1:
            return []
        else:
            areas = []
            for i in range(polygon.GetGeometryCount()):
                if i > 0:
                    c_ring = polygon.GetGeometryRef(i)
                    tmp_poly = ogr.Geometry(ogr.wkbPolygon)
                    tmp_poly.AddGeometry(c_ring)
                    areas.append(tmp_poly.Area())
            return areas

    vecDS = gdal.OpenEx(vec_file, gdal.OF_VECTOR)
    if vecDS is None:
        raise Exception("Could not open '{}'".format(vec_file))

    vec_lyr_obj = vecDS.GetLayerByName(vec_lyr)
    if vec_lyr_obj is None:
        raise Exception("Could not open layer '{}'".format(vec_lyr))

    vec_lyr_obj.ResetReading()
    n_feats = vec_lyr_obj.GetFeatureCount(True)
    pbar = tqdm.tqdm(total=n_feats)
    vec_lyr_obj.ResetReading()
    feat = vec_lyr_obj.GetNextFeature()
    hole_areas = []
    while feat is not None:
        geom_ref = feat.GetGeometryRef()
        if geom_ref.GetGeometryName().lower() == "multipolygon":
            out_geom = ogr.Geometry(ogr.wkbMultiPolygon)
            for i in range(0, geom_ref.GetGeometryCount()):
                g = geom_ref.GetGeometryRef(i)
                areas = _calc_hole_area(g)
                if len(areas) > 0:
                    hole_areas += areas
        elif geom_ref.GetGeometryName().lower() == "polygon":
            areas = _calc_hole_area(geom_ref)
            if len(areas) > 0:
                hole_areas += areas

        feat = vec_lyr_obj.GetNextFeature()
        pbar.update(1)

    pbar.close()
    vecDS = None
    return hole_areas


def remove_polygon_area(
    vec_file,
    vec_lyr,
    out_format,
    out_vec_file,
    out_vec_lyr,
    area_thres,
    del_exist_vec=False,
):
    """
    Delete polygons with an area below a defined threshold.

    :param vec_file: input vector file
    :param vec_lyr: input vector layer within the input file.
    :param out_format: the format driver for the output vector
                       file (e.g., GPKG, ESRI Shapefile).
    :param out_vec_file: output file path for the vector.
    :param out_vec_lyr: output vector layer name.
    :param area_thres: threshold below which polygons are removed.
    :param del_exist_vec: remove output file if it exists.
    """
    from osgeo import gdal
    from osgeo import ogr
    import tqdm

    gdal.UseExceptions()

    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise Exception(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(out_vec_file)
            )

    vecDS = gdal.OpenEx(vec_file, gdal.OF_VECTOR)
    if vecDS is None:
        raise Exception("Could not open '{}'".format(vec_file))

    vec_lyr_obj = vecDS.GetLayerByName(vec_lyr)
    if vec_lyr_obj is None:
        raise Exception("Could not open layer '{}'".format(vec_lyr))
    lyr_spat_ref = vec_lyr_obj.GetSpatialRef()
    geom_type = vec_lyr_obj.GetGeomType()

    out_driver = ogr.GetDriverByName(out_format)
    result_ds = out_driver.CreateDataSource(out_vec_file)
    if result_ds is None:
        raise Exception("Could not open '{}'".format(out_vec_file))

    result_lyr = result_ds.CreateLayer(out_vec_lyr, lyr_spat_ref, geom_type=geom_type)
    if result_lyr is None:
        raise Exception("Could not open layer '{}'".format(out_vec_lyr))

    featDefn = result_lyr.GetLayerDefn()

    openTransaction = False
    vec_lyr_obj.ResetReading()
    n_feats = vec_lyr_obj.GetFeatureCount(True)
    counter = 0
    pbar = tqdm.tqdm(total=n_feats)
    vec_lyr_obj.ResetReading()
    feat = vec_lyr_obj.GetNextFeature()
    while feat is not None:
        if not openTransaction:
            result_lyr.StartTransaction()
            openTransaction = True

        geom_ref = feat.GetGeometryRef()
        if geom_ref.GetGeometryName().lower() == "multipolygon":
            out_geom = ogr.Geometry(ogr.wkbMultiPolygon)
            n_geoms = 0
            for i in range(0, geom_ref.GetGeometryCount()):
                g = geom_ref.GetGeometryRef(i)
                if g.Area() > area_thres:
                    out_geom.AddGeometry(g)
                    n_geoms += 1
            if n_geoms > 0:
                outFeat = ogr.Feature(featDefn)
                outFeat.SetGeometry(out_geom)
                result_lyr.CreateFeature(outFeat)
        elif geom_ref.GetGeometryName().lower() == "polygon":
            if geom_ref.Area() > area_thres:
                outFeat = ogr.Feature(featDefn)
                outFeat.SetGeometry(geom_ref)
                result_lyr.CreateFeature(outFeat)

        if ((counter % 20000) == 0) and openTransaction:
            result_lyr.CommitTransaction()
            openTransaction = False

        feat = vec_lyr_obj.GetNextFeature()
        counter = counter + 1
        pbar.update(1)

    if openTransaction:
        result_lyr.CommitTransaction()
        openTransaction = False
    result_lyr.SyncToDisk()
    pbar.close()

    vecDS = None
    result_ds = None


def vec_lyr_intersection(
    vec_file,
    vec_lyr,
    vec_over_file,
    vec_over_lyr,
    out_vec_file,
    out_vec_lyr=None,
    out_format="GPKG",
    del_exist_vec=False,
):
    """
    A function which performs an intersection between the vector
    layer and the overlain vector.

    :param vec_file: Input vector file path.
    :param vec_lyr: Input vector layer name.
    :param vec_over_file: The vector file overlained on the input vector file.
    :param vec_over_lyr: The vector layer overlained on the input vector file.
    :param out_vec_file: The output vector file path.
    :param out_vec_lyr: The output vector layer name.
    :param out_format: The output file format of the vector file.
    :param del_exist_vec: remove output file if it exists.

    """
    from osgeo import gdal
    from osgeo import ogr
    import rsgislib
    import os
    import tqdm

    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise Exception(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(out_vec_file)
            )

    if out_vec_lyr is None:
        out_vec_lyr = os.path.splitext(os.path.basename(out_vec_file))[0]

    gdal.UseExceptions()
    vec_bbox = rsgislib.vectorutils.get_vec_layer_extent(vec_file, vec_lyr)

    ds_in_vec = gdal.OpenEx(vec_file, gdal.OF_READONLY)
    if ds_in_vec is None:
        raise Exception("Could not open '{}'".format(vec_file))

    lyr_in_vec = ds_in_vec.GetLayerByName(vec_lyr)
    if lyr_in_vec is None:
        raise Exception("Could not find layer '{}'".format(vec_lyr))
    spat_ref = lyr_in_vec.GetSpatialRef()
    geom_type = lyr_in_vec.GetGeomType()

    ds_over_vec = gdal.OpenEx(vec_over_file, gdal.OF_READONLY)
    if ds_over_vec is None:
        raise Exception("Could not open '{}'".format(vec_over_file))

    lyr_over_vec = ds_over_vec.GetLayerByName(vec_over_lyr)
    if lyr_over_vec is None:
        raise Exception("Could not find layer '{}'".format(vec_over_lyr))

    out_driver = ogr.GetDriverByName(out_format)
    out_ds_obj = out_driver.CreateDataSource(out_vec_file)
    out_lyr_obj = out_ds_obj.CreateLayer(out_vec_lyr, spat_ref, geom_type=geom_type)
    feat_defn = out_lyr_obj.GetLayerDefn()

    geom_collect = ogr.Geometry(ogr.wkbGeometryCollection)
    n_obj_feats = lyr_over_vec.GetFeatureCount(True)
    geom_pbar = tqdm.tqdm(total=n_obj_feats, leave=True)
    lyr_over_vec.ResetReading()
    in_obj_feat = lyr_over_vec.GetNextFeature()
    while in_obj_feat:
        geom = in_obj_feat.GetGeometryRef()
        if geom is not None:
            geom_collect.AddGeometry(geom)
        in_obj_feat = lyr_over_vec.GetNextFeature()
        geom_pbar.update(1)
    geom_pbar.close()

    n_feats = lyr_in_vec.GetFeatureCount(True)
    pbar = tqdm.tqdm(total=n_feats, leave=True)
    open_transaction = False
    counter = 0
    lyr_in_vec.ResetReading()
    in_feature = lyr_in_vec.GetNextFeature()
    while in_feature:
        pbar.update(1)
        if not open_transaction:
            out_lyr_obj.StartTransaction()
            open_transaction = True

        in_geom = in_feature.GetGeometryRef()
        if in_geom is not None:
            op_out_geom = geom_collect.Intersection(in_geom)

            if (op_out_geom is not None) and (op_out_geom.GetGeometryCount() > 0):
                for i in range(op_out_geom.GetGeometryCount()):
                    c_geom = op_out_geom.GetGeometryRef(i)

                    if (
                        (c_geom.GetGeometryName().upper() == "POLYGON")
                        or (c_geom.GetGeometryName().upper() == "MULTIPOLYGON")
                    ) and (
                        (geom_type == ogr.wkbMultiPolygon)
                        or (geom_type == ogr.wkbPolygon)
                    ):
                        out_feat = ogr.Feature(feat_defn)
                        out_feat.SetGeometry(c_geom)
                        out_lyr_obj.CreateFeature(out_feat)
                        out_feat = None
                    elif (
                        (c_geom.GetGeometryName().upper() == "LINESTRING")
                        or (c_geom.GetGeometryName().upper() == "MULTILINESTRING")
                    ) and (
                        (geom_type == ogr.wkbMultiLineString)
                        or (geom_type == ogr.wkbLineString)
                    ):
                        out_feat = ogr.Feature(feat_defn)
                        out_feat.SetGeometry(c_geom)
                        out_lyr_obj.CreateFeature(out_feat)
                        out_feat = None
                    elif (
                        (c_geom.GetGeometryName().upper() == "POINT")
                        or (c_geom.GetGeometryName().upper() == "MULTIPOINT")
                    ) and (
                        (geom_type == ogr.wkbMultiPoint) or (geom_type == ogr.wkbPoint)
                    ):
                        out_feat = ogr.Feature(feat_defn)
                        out_feat.SetGeometry(c_geom)
                        out_lyr_obj.CreateFeature(out_feat)
                        out_feat = None

        if ((counter % 20000) == 0) and open_transaction:
            out_lyr_obj.CommitTransaction()
            open_transaction = False

        in_feature = lyr_in_vec.GetNextFeature()
        counter = counter + 1

    if open_transaction:
        out_lyr_obj.CommitTransaction()
        open_transaction = False
    pbar.close()
    out_lyr_obj.SyncToDisk()
    out_ds_obj = None
    ds_in_vec = None
    ds_over_vec = None


def vec_lyr_difference(
    vec_file,
    vec_lyr,
    vec_over_file,
    vec_over_lyr,
    out_vec_file,
    out_vec_lyr=None,
    out_format="GPKG",
    symmetric=False,
    del_exist_vec=False,
):
    """
    A function which performs an difference between the vector layer and the overlain vector.

    :param vec_file: Input vector file path.
    :param vec_lyr: Input vector layer name.
    :param vec_over_file: The vector file overlained on the input vector file.
    :param vec_over_lyr: The vector layer overlained on the input vector file.
    :param out_vec_file: The output vector file path.
    :param out_vec_lyr: The output vector layer name.
    :param out_format: The output file format of the vector file.
    :param symmetric: If True then the symmetric difference will be taken.
    :param del_exist_vec: remove output file if it exists.

    """
    from osgeo import gdal
    from osgeo import ogr
    import rsgislib
    import os
    import tqdm

    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise Exception(
                "The output vector file ({}) already "
                "exists, remove it and re-run.".format(out_vec_file)
            )

    if out_vec_lyr is None:
        out_vec_lyr = os.path.splitext(os.path.basename(out_vec_file))[0]

    gdal.UseExceptions()
    vec_bbox = rsgislib.vectorutils.get_vec_layer_extent(vec_file, vec_lyr)

    ds_in_vec = gdal.OpenEx(vec_file, gdal.OF_READONLY)
    if ds_in_vec is None:
        raise Exception("Could not open '{}'".format(vec_file))

    lyr_in_vec = ds_in_vec.GetLayerByName(vec_lyr)
    if lyr_in_vec is None:
        raise Exception("Could not find layer '{}'".format(vec_lyr))
    spat_ref = lyr_in_vec.GetSpatialRef()
    geom_type = lyr_in_vec.GetGeomType()

    ds_over_vec = gdal.OpenEx(vec_over_file, gdal.OF_READONLY)
    if ds_over_vec is None:
        raise Exception("Could not open '{}'".format(vec_over_file))

    lyr_over_vec = ds_over_vec.GetLayerByName(vec_over_lyr)
    if lyr_over_vec is None:
        raise Exception("Could not find layer '{}'".format(vec_over_lyr))

    out_driver = ogr.GetDriverByName(out_format)
    out_ds_obj = out_driver.CreateDataSource(out_vec_file)
    out_lyr_obj = out_ds_obj.CreateLayer(out_vec_lyr, spat_ref, geom_type=geom_type)
    feat_defn = out_lyr_obj.GetLayerDefn()

    geoms_lst = list()
    n_obj_feats = lyr_over_vec.GetFeatureCount(True)
    geom_pbar = tqdm.tqdm(total=n_obj_feats, leave=True)
    lyr_over_vec.ResetReading()
    in_obj_feat = lyr_over_vec.GetNextFeature()
    while in_obj_feat:
        geom = in_obj_feat.GetGeometryRef()
        if geom is not None:
            geoms_lst.append(geom.Clone())
        in_obj_feat = lyr_over_vec.GetNextFeature()
        geom_pbar.update(1)
    geom_pbar.close()

    n_feats = lyr_in_vec.GetFeatureCount(True)
    pbar = tqdm.tqdm(total=n_feats, leave=True)
    open_transaction = False
    counter = 0
    lyr_in_vec.ResetReading()
    in_feature = lyr_in_vec.GetNextFeature()
    while in_feature:
        pbar.update(1)
        if not open_transaction:
            out_lyr_obj.StartTransaction()
            open_transaction = True

        in_geom = in_feature.GetGeometryRef()
        if in_geom is not None:
            for over_geom in geoms_lst:
                if in_geom.Intersect(over_geom):
                    if symmetric:
                        op_out_geom = in_geom.SymmetricDifference(over_geom)
                    else:
                        op_out_geom = in_geom.Difference(over_geom)
                    if (op_out_geom is not None) and (
                        op_out_geom.GetGeometryCount() > 0
                    ):
                        for i in range(op_out_geom.GetGeometryCount()):
                            c_geom = op_out_geom.GetGeometryRef(i)
                            if (
                                (c_geom.GetGeometryName().upper() == "POLYGON")
                                or (c_geom.GetGeometryName().upper() == "MULTIPOLYGON")
                            ) and (
                                (geom_type == ogr.wkbMultiPolygon)
                                or (geom_type == ogr.wkbPolygon)
                            ):
                                out_feat = ogr.Feature(feat_defn)
                                out_feat.SetGeometry(c_geom)
                                out_lyr_obj.CreateFeature(out_feat)
                                out_feat = None
                            elif (
                                (c_geom.GetGeometryName().upper() == "LINESTRING")
                                or (
                                    c_geom.GetGeometryName().upper()
                                    == "MULTILINESTRING"
                                )
                            ) and (
                                (geom_type == ogr.wkbMultiLineString)
                                or (geom_type == ogr.wkbLineString)
                            ):
                                out_feat = ogr.Feature(feat_defn)
                                out_feat.SetGeometry(c_geom)
                                out_lyr_obj.CreateFeature(out_feat)
                                out_feat = None
                            elif (
                                (c_geom.GetGeometryName().upper() == "POINT")
                                or (c_geom.GetGeometryName().upper() == "MULTIPOINT")
                            ) and (
                                (geom_type == ogr.wkbMultiPoint)
                                or (geom_type == ogr.wkbPoint)
                            ):
                                out_feat = ogr.Feature(feat_defn)
                                out_feat.SetGeometry(c_geom)
                                out_lyr_obj.CreateFeature(out_feat)
                                out_feat = None

        if ((counter % 20000) == 0) and open_transaction:
            out_lyr_obj.CommitTransaction()
            open_transaction = False

        in_feature = lyr_in_vec.GetNextFeature()
        counter = counter + 1

    if open_transaction:
        out_lyr_obj.CommitTransaction()
        open_transaction = False
    pbar.close()
    out_lyr_obj.SyncToDisk()
    out_ds_obj = None
    ds_in_vec = None
    ds_over_vec = None


def get_geom_pts(geom, pts_lst=None):
    """
    Recursive function which extracts all the points within the an OGR geometry.

    :param geom: The geometry from with the points are extracted.
    :param pts_lst: The list for the points, if None a list will be created.
    :return: a list of points.

    """
    from osgeo import ogr

    if pts_lst is None:
        pts_lst = list()

    if geom is not None:
        if geom.GetGeometryType() == ogr.wkbPoint:
            pts_lst.append(geom)
        else:
            n_geoms = geom.GetGeometryCount()
            for n in range(0, n_geoms):
                c_geom = geom.GetGeometryRef(n)
                n_pts = c_geom.GetPointCount()
                if n_pts == 0:
                    get_geom_pts(c_geom, pts_lst)
                else:
                    for i in range(0, n_pts):
                        pt = c_geom.GetPoint(i)
                        pts_lst.append(pt)
    return pts_lst


def vec_intersects_vec(vec_base_file, vec_base_lyr, vec_comp_file, vec_comp_lyr):
    """
    Function to test whether the comparison vector layer intersects with the
    base vector layer.

    Note. This function iterates through the geometries of both files performing
    a comparison and therefore can be very slow to execute for large vector files.

    :param vec_base_file: vector layer file used as the base layer
    :param vec_base_lyr: vector layer used as the base layer
    :param vec_comp_file: vector layer file used as the comparison layer
    :param vec_comp_lyr: vector layer used as the comparison layer
    :return: boolean

    """
    import osgeo.gdal as gdal
    import tqdm

    gdal.UseExceptions()

    dsVecBaseObj = gdal.OpenEx(vec_base_file, gdal.OF_READONLY)
    if dsVecBaseObj is None:
        raise Exception("Could not open '{}'".format(vec_base_file))

    lyrVecBaseObj = dsVecBaseObj.GetLayerByName(vec_base_lyr)
    if lyrVecBaseObj is None:
        raise Exception("Could not find layer '{}'".format(vec_base_lyr))

    dsVecCompObj = gdal.OpenEx(vec_comp_file, gdal.OF_READONLY)
    if dsVecCompObj is None:
        raise Exception("Could not open '{}'".format(vec_comp_file))

    lyrVecCompObj = dsVecCompObj.GetLayerByName(vec_comp_lyr)
    if lyrVecCompObj is None:
        raise Exception("Could not find layer '{}'".format(vec_comp_lyr))

    n_feats = lyrVecBaseObj.GetFeatureCount(True)
    pbar = tqdm.tqdm(total=n_feats)
    does_intersect = False
    lyrVecBaseObj.ResetReading()
    base_feat = lyrVecBaseObj.GetNextFeature()
    while base_feat is not None:
        base_geom = base_feat.GetGeometryRef()
        if base_geom is not None:
            lyrVecCompObj.ResetReading()
            comp_feat = lyrVecCompObj.GetNextFeature()
            while comp_feat is not None:
                comp_geom = comp_feat.GetGeometryRef()
                if comp_geom is not None:
                    if base_geom.Intersects(comp_geom):
                        does_intersect = True
                        break
                comp_feat = lyrVecCompObj.GetNextFeature()
        if does_intersect:
            break
        pbar.update(1)
        base_feat = lyrVecBaseObj.GetNextFeature()

    dsVecBaseObj = None
    dsVecCompObj = None

    return does_intersect


def vec_overlaps_vec(vec_base_file, vec_base_lyr, vec_comp_file, vec_comp_lyr):
    """
    Function to test whether the comparison vector layer overlaps with the
    base vector layer.

    Note. This function iterates through the geometries of both files performing
    a comparison and therefore can be very slow to execute for large vector files.

    :param vec_base_file: vector layer file used as the base layer
    :param vec_base_lyr: vector layer used as the base layer
    :param vec_comp_file: vector layer file used as the comparison layer
    :param vec_comp_lyr: vector layer used as the comparison layer
    :return: boolean

    """
    import osgeo.gdal as gdal
    import tqdm

    gdal.UseExceptions()

    dsVecBaseObj = gdal.OpenEx(vec_base_file, gdal.OF_READONLY)
    if dsVecBaseObj is None:
        raise Exception("Could not open '{}'".format(vec_base_file))

    lyrVecBaseObj = dsVecBaseObj.GetLayerByName(vec_base_lyr)
    if lyrVecBaseObj is None:
        raise Exception("Could not find layer '{}'".format(vec_base_lyr))

    dsVecCompObj = gdal.OpenEx(vec_comp_file, gdal.OF_READONLY)
    if dsVecCompObj is None:
        raise Exception("Could not open '{}'".format(vec_comp_file))

    lyrVecCompObj = dsVecCompObj.GetLayerByName(vec_comp_lyr)
    if lyrVecCompObj is None:
        raise Exception("Could not find layer '{}'".format(vec_comp_lyr))

    n_feats = lyrVecBaseObj.GetFeatureCount(True)
    pbar = tqdm.tqdm(total=n_feats)
    does_overlap = False
    lyrVecBaseObj.ResetReading()
    base_feat = lyrVecBaseObj.GetNextFeature()
    while base_feat is not None:
        base_geom = base_feat.GetGeometryRef()
        if base_geom is not None:
            lyrVecCompObj.ResetReading()
            comp_feat = lyrVecCompObj.GetNextFeature()
            while comp_feat is not None:
                comp_geom = comp_feat.GetGeometryRef()
                if comp_geom is not None:
                    if comp_geom.Overlaps(base_geom):
                        does_overlap = True
                        break
                comp_feat = lyrVecCompObj.GetNextFeature()
        if does_overlap:
            break
        pbar.update(1)
        base_feat = lyrVecBaseObj.GetNextFeature()

    dsVecBaseObj = None
    dsVecCompObj = None

    return does_overlap


def vec_within_vec(vec_base_file, vec_base_lyr, vec_comp_file, vec_comp_lyr):
    """
    Function to test whether the comparison vector layer within with the
    base vector layer.

    Note. This function iterates through the geometries of both files performing
    a comparison and therefore can be very slow to execute for large vector files.

    :param vec_base_file: vector layer file used as the base layer
    :param vec_base_lyr: vector layer used as the base layer
    :param vec_comp_file: vector layer file used as the comparison layer
    :param vec_comp_lyr: vector layer used as the comparison layer
    :return: boolean

    """
    import osgeo.gdal as gdal
    import tqdm

    gdal.UseExceptions()

    dsVecBaseObj = gdal.OpenEx(vec_base_file, gdal.OF_READONLY)
    if dsVecBaseObj is None:
        raise Exception("Could not open '{}'".format(vec_base_file))

    lyrVecBaseObj = dsVecBaseObj.GetLayerByName(vec_base_lyr)
    if lyrVecBaseObj is None:
        raise Exception("Could not find layer '{}'".format(vec_base_lyr))

    dsVecCompObj = gdal.OpenEx(vec_comp_file, gdal.OF_READONLY)
    if dsVecCompObj is None:
        raise Exception("Could not open '{}'".format(vec_comp_file))

    lyrVecCompObj = dsVecCompObj.GetLayerByName(vec_comp_lyr)
    if lyrVecCompObj is None:
        raise Exception("Could not find layer '{}'".format(vec_comp_lyr))

    n_feats = lyrVecCompObj.GetFeatureCount(True)
    pbar = tqdm.tqdm(total=n_feats)
    is_within = True

    lyrVecCompObj.ResetReading()
    comp_feat = lyrVecCompObj.GetNextFeature()
    while comp_feat is not None:
        comp_geom = comp_feat.GetGeometryRef()
        comp_feat_within = False
        if comp_geom is not None:
            lyrVecBaseObj.ResetReading()
            base_feat = lyrVecBaseObj.GetNextFeature()
            while base_feat is not None:
                base_geom = base_feat.GetGeometryRef()
                if base_geom is not None:
                    if comp_geom.Within(base_geom):
                        comp_feat_within = True
                        break
                base_feat = lyrVecBaseObj.GetNextFeature()

        if not comp_feat_within:
            is_within = False
            break
        pbar.update(1)
        comp_feat = lyrVecCompObj.GetNextFeature()

    dsVecBaseObj = None
    dsVecCompObj = None

    return is_within


def vec_contains_vec(vec_base_file, vec_base_lyr, vec_comp_file, vec_comp_lyr):
    """
    Function to test whether the base vector layer contains with the
    comparison vector layer.

    Note. This function iterates through the geometries of both files performing
    a comparison and therefore can be very slow to execute for large vector files.

    :param vec_base_file: vector layer file used as the base layer
    :param vec_base_lyr: vector layer used as the base layer
    :param vec_comp_file: vector layer file used as the comparison layer
    :param vec_comp_lyr: vector layer used as the comparison layer
    :return: boolean

    """
    import osgeo.gdal as gdal
    import tqdm

    gdal.UseExceptions()

    dsVecBaseObj = gdal.OpenEx(vec_base_file, gdal.OF_READONLY)
    if dsVecBaseObj is None:
        raise Exception("Could not open '{}'".format(vec_base_file))

    lyrVecBaseObj = dsVecBaseObj.GetLayerByName(vec_base_lyr)
    if lyrVecBaseObj is None:
        raise Exception("Could not find layer '{}'".format(vec_base_lyr))

    dsVecCompObj = gdal.OpenEx(vec_comp_file, gdal.OF_READONLY)
    if dsVecCompObj is None:
        raise Exception("Could not open '{}'".format(vec_comp_file))

    lyrVecCompObj = dsVecCompObj.GetLayerByName(vec_comp_lyr)
    if lyrVecCompObj is None:
        raise Exception("Could not find layer '{}'".format(vec_comp_lyr))

    n_feats = lyrVecCompObj.GetFeatureCount(True)
    pbar = tqdm.tqdm(total=n_feats)
    does_contain = True

    lyrVecCompObj.ResetReading()
    comp_feat = lyrVecCompObj.GetNextFeature()
    while comp_feat is not None:
        comp_geom = comp_feat.GetGeometryRef()
        comp_feat_contained = False
        if comp_geom is not None:
            lyrVecBaseObj.ResetReading()
            base_feat = lyrVecBaseObj.GetNextFeature()
            while base_feat is not None:
                base_geom = base_feat.GetGeometryRef()
                if base_geom is not None:
                    if base_geom.Contains(comp_geom):
                        comp_feat_contained = True
                        break
                base_feat = lyrVecBaseObj.GetNextFeature()

        if not comp_feat_contained:
            does_contain = False
            break
        pbar.update(1)
        comp_feat = lyrVecCompObj.GetNextFeature()

    dsVecBaseObj = None
    dsVecCompObj = None

    return does_contain


def vec_touches_vec(vec_base_file, vec_base_lyr, vec_comp_file, vec_comp_lyr):
    """
    Function to test whether the comparison vector layer touches the
    base vector layer.

    Note. This function iterates through the geometries of both files performing
    a comparison and therefore can be very slow to execute for large vector files.

    :param vec_base_file: vector layer file used as the base layer
    :param vec_base_lyr: vector layer used as the base layer
    :param vec_comp_file: vector layer file used as the comparison layer
    :param vec_comp_lyr: vector layer used as the comparison layer
    :return: boolean

    """
    import osgeo.gdal as gdal
    import tqdm

    gdal.UseExceptions()

    dsVecBaseObj = gdal.OpenEx(vec_base_file, gdal.OF_READONLY)
    if dsVecBaseObj is None:
        raise Exception("Could not open '{}'".format(vec_base_file))

    lyrVecBaseObj = dsVecBaseObj.GetLayerByName(vec_base_lyr)
    if lyrVecBaseObj is None:
        raise Exception("Could not find layer '{}'".format(vec_base_lyr))

    dsVecCompObj = gdal.OpenEx(vec_comp_file, gdal.OF_READONLY)
    if dsVecCompObj is None:
        raise Exception("Could not open '{}'".format(vec_comp_file))

    lyrVecCompObj = dsVecCompObj.GetLayerByName(vec_comp_lyr)
    if lyrVecCompObj is None:
        raise Exception("Could not find layer '{}'".format(vec_comp_lyr))

    n_feats = lyrVecBaseObj.GetFeatureCount(True)
    pbar = tqdm.tqdm(total=n_feats)
    does_touch = False

    lyrVecBaseObj.ResetReading()
    base_feat = lyrVecBaseObj.GetNextFeature()
    while base_feat is not None:
        base_geom = base_feat.GetGeometryRef()
        if base_geom is not None:
            lyrVecCompObj.ResetReading()
            comp_feat = lyrVecCompObj.GetNextFeature()
            while comp_feat is not None:
                comp_geom = comp_feat.GetGeometryRef()
                if comp_geom is not None:
                    if comp_geom.Touches(base_geom):
                        does_touch = True
                        break
                comp_feat = lyrVecCompObj.GetNextFeature()
        if does_touch:
            break
        pbar.update(1)
        base_feat = lyrVecBaseObj.GetNextFeature()

    dsVecBaseObj = None
    dsVecCompObj = None

    return does_touch


def vec_crosses_vec(vec_base_file, vec_base_lyr, vec_comp_file, vec_comp_lyr):
    """
    Function to test whether the comparison vector layer touches the
    base vector layer.

    Note. This function iterates through the geometries of both files performing
    a comparison and therefore can be very slow to execute for large vector files.

    :param vec_base_file: vector layer file used as the base layer
    :param vec_base_lyr: vector layer used as the base layer
    :param vec_comp_file: vector layer file used as the comparison layer
    :param vec_comp_lyr: vector layer used as the comparison layer
    :return: boolean

    """
    import osgeo.gdal as gdal
    import tqdm

    gdal.UseExceptions()

    dsVecBaseObj = gdal.OpenEx(vec_base_file, gdal.OF_READONLY)
    if dsVecBaseObj is None:
        raise Exception("Could not open '{}'".format(vec_base_file))

    lyrVecBaseObj = dsVecBaseObj.GetLayerByName(vec_base_lyr)
    if lyrVecBaseObj is None:
        raise Exception("Could not find layer '{}'".format(vec_base_lyr))

    dsVecCompObj = gdal.OpenEx(vec_comp_file, gdal.OF_READONLY)
    if dsVecCompObj is None:
        raise Exception("Could not open '{}'".format(vec_comp_file))

    lyrVecCompObj = dsVecCompObj.GetLayerByName(vec_comp_lyr)
    if lyrVecCompObj is None:
        raise Exception("Could not find layer '{}'".format(vec_comp_lyr))

    n_feats = lyrVecBaseObj.GetFeatureCount(True)
    pbar = tqdm.tqdm(total=n_feats)
    does_cross = False

    lyrVecBaseObj.ResetReading()
    base_feat = lyrVecBaseObj.GetNextFeature()
    while base_feat is not None:
        base_geom = base_feat.GetGeometryRef()
        if base_geom is not None:
            lyrVecCompObj.ResetReading()
            comp_feat = lyrVecCompObj.GetNextFeature()
            while comp_feat is not None:
                comp_geom = comp_feat.GetGeometryRef()
                if comp_geom is not None:
                    if comp_geom.Crosses(base_geom):
                        does_cross = True
                        break
                comp_feat = lyrVecCompObj.GetNextFeature()
        if does_cross:
            break
        pbar.update(1)
        base_feat = lyrVecBaseObj.GetNextFeature()

    dsVecBaseObj = None
    dsVecCompObj = None

    return does_cross


def get_feat_envs(vec_file, vec_lyr):
    """
    A function which returns a list of bounding boxes for each feature
    within the vector layer.

    :param vec_file: vector file.
    :param vec_lyr: layer within the vector file.
    :returns: list of BBOXs
    """
    dsVecFile = gdal.OpenEx(vec_file, gdal.OF_VECTOR)
    if dsVecFile is None:
        raise Exception("Could not open '{}'".format(vec_file))

    vec_lyr_obj = dsVecFile.GetLayerByName(vec_lyr)
    if vec_lyr_obj is None:
        raise Exception("Could not find layer '{}'".format(vec_lyr))

    openTransaction = False
    nFeats = vec_lyr_obj.GetFeatureCount(True)
    step = math.floor(nFeats / 10)
    feedback = 10
    feedback_next = step
    counter = 0
    print("Started .0.", end="", flush=True)
    outenvs = []
    # loop through the input features
    inFeature = vec_lyr_obj.GetNextFeature()
    while inFeature:
        if (nFeats > 10) and (counter == feedback_next):
            print(".{}.".format(feedback), end="", flush=True)
            feedback_next = feedback_next + step
            feedback = feedback + 10

        # get the input geometry
        geom = inFeature.GetGeometryRef()
        if geom is not None:
            outenvs.append(geom.GetEnvelope())

        inFeature = vec_lyr_obj.GetNextFeature()
        counter = counter + 1
    print(" Completed")
    dsVecFile = None
    return outenvs
