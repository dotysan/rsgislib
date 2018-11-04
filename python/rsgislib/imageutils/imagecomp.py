############################################################################
#  imagecomp.py
#
#  Copyright 2017 RSGISLib.
#
#  RSGISLib: 'The remote sensing and GIS Software Library'
#
#  RSGISLib is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  RSGISLib is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with RSGISLib.  If not, see <http://www.gnu.org/licenses/>.
#
#
# Purpose:  Provide a set of utilities for creating image composites
#
# Author: Pete Bunting
# Email: petebunting@mac.com
# Date: 04/10/2017
# Version: 1.0
#
# History:
# Version 1.0 - Created.
#
############################################################################

import rsgislib
import rsgislib.imagecalc
import rsgislib.imagecalc.calcindices
import rsgislib.imageutils
import rsgislib.rastergis

import glob
import os
import os.path
import numpy
import shutil

import osgeo.gdal
import rios.rat


def createMaxNDVIComposite(inImgsPattern, rBand, nBand, outRefImg, outCompImg, tmpPath='./tmp', gdalformat='KEA', dataType=None, calcStats=True):
    """
Create an image composite from multiple input images where the pixel brought through into the composite is the one with
the maximum NDVI.

* inImgsPattern - is a pattern (ready for glob.glob(inImgsPattern)) so needs an * within the pattern to find the input image files.
* rBand - is the image band within the input images (same for all) for the red band - note band indexing starts at 1.
* nBand - is the image band within the input images (same for all) for the nir band - note band indexing starts at 1.
* outRefImg - is the output reference image which details which input image is forming the output image pixel value (Note. this file will always be a KEA file as RAT is used).
* outCompImg - is the output composite image for which gdalformat and dataType define the format and data type.
* tmpPath - is a temp path for intemediate files, if this path doesn't exist is will be created and deleted at runtime.
* gdalformat - is the output file format of the outCompImg, any GDAL compatable format is OK (Defaut is KEA).
* dataType - is the data type of the output image (outCompImg). If None is provided then the data type of the first input image will be used (Default None). 
* calcStats calculate image statics and pyramids (Default=True)
    """
    rsgisUtils = rsgislib.RSGISPyUtils()
    uidStr = rsgisUtils.uidGenerator()
    
    # Get List of input images:
    inImages = glob.glob(inImgsPattern)
    
    if len(inImages) > 1:
        tmpPresent = True
        if not os.path.exists(tmpPath):
            os.makedirs(tmpPath)
            tmpPresent = False 
        
        refLayersPath = os.path.join(tmpPath, 'RefLyrs_'+uidStr)
        
        refImgTmpPresent = True
        if not os.path.exists(refLayersPath):
            os.makedirs(refLayersPath)
            refImgTmpPresent = False
        
        if dataType is None:
            rsgisUtils.getRSGISLibDataTypeFromImg(inImages[0])
        
        numInLyrs = len(inImages)
        
        numpy.random.seed(5)
        red = numpy.random.randint(1, 255, numInLyrs+1, int)
        red[0] = 0
        numpy.random.seed(2)
        green = numpy.random.randint(1, 255, numInLyrs+1, int)
        green[0] = 0
        numpy.random.seed(9)
        blue = numpy.random.randint(1, 255, numInLyrs+1, int)
        blue[0] = 0
        alpha = numpy.zeros_like(blue)
        alpha[...] = 255
        imgLyrs = numpy.empty(numInLyrs+1, dtype=numpy.dtype('a255'))
            
        # Generate Comp Ref layers:
        refLyrsLst = []
        idx = 1
        for img in inImages:
            print('In Image ('+str(idx) + '):\t' + img)
            imgLyrs[idx] = os.path.basename(img)
            baseImgName = os.path.splitext(os.path.basename(img))[0]
            refLyrImg = os.path.join(refLayersPath, baseImgName+'_ndvi.kea')
            rsgislib.imagecalc.calcindices.calcNDVI(img, rBand, nBand, refLyrImg, False)
            refLyrsLst.append(refLyrImg)
            idx = idx + 1
        imgLyrs[0] = ""
    
        # Create REF Image
        rsgislib.imagecalc.getImgIdxForStat(refLyrsLst, outRefImg, 'KEA', -999, rsgislib.SUMTYPE_MAX)
        if calcStats:
            # Pop Ref Image with stats
            rsgislib.rastergis.populateStats(outRefImg, True, True, True)
            
            # Open the clumps dataset as a gdal dataset
            ratDataset = osgeo.gdal.Open(outRefImg, osgeo.gdal.GA_Update)
            
            # Write colours to RAT
            rios.rat.writeColumn(ratDataset, "Red", red)
            rios.rat.writeColumn(ratDataset, "Green", green)
            rios.rat.writeColumn(ratDataset, "Blue", blue)
            rios.rat.writeColumn(ratDataset, "Alpha", alpha)
            rios.rat.writeColumn(ratDataset, "Image", imgLyrs)
            
            ratDataset = None
        
        # Create Composite Image
        rsgislib.imageutils.createRefImgCompositeImg(inImages, outCompImg, outRefImg, gdalformat, dataType, 0.0)
        
        if calcStats:
            # Calc Stats
            rsgislib.imageutils.popImageStats(outCompImg, usenodataval=True, nodataval=0, calcpyramids=True)
    
        if not refImgTmpPresent:
            shutil.rmtree(refLayersPath, ignore_errors=True)
    
        if not tmpPresent:
            shutil.rmtree(tmpPath, ignore_errors=True)
    elif len(inImages) == 1:
        print("Only 1 Input Image, Just Copying File to output")
        shutil.copy(inImages[0], outCompImg)
    else:
        raise rsgislib.RSGISPyException("There were no input images for " + inImgsPattern)



def createMaxNDVINDWICompositeLandsat(inImgsPattern, outRefImg, outCompImg, outMskImg, tmpPath='./tmp', gdalformat='KEA', dataType=None, calcStats=True):
    """
Create an image composite from multiple input images where the pixel brought through into the composite is the one with
the maximum NDVI over land and NDWI over water. A mask of land and water regions is also produced. Landsat 8 images are 
identified as image file names are expected to start 'LS8'. If composite includes a mix of LS8 and LS7 images then the 
LS8 images are submitted to match the images bands of LS7 (i.e., coastal band removed).

* inImgsPattern - is a pattern (ready for glob.glob(inImgsPattern)) so needs an * within the pattern to find the input image files.
* outRefImg - is the output reference image which details which input image is forming the output image pixel value (Note. this file will always be a KEA file as RAT is used).
* outCompImg - is the output composite image for which gdalformat and dataType define the format and data type.
* outMskImg - is the output mask image for regions of water and land where ndvi vs ndwi are used (0=nodata, 1=land, 2=water)
* tmpPath - is a temp path for intemediate files, if this path doesn't exist is will be created and deleted at runtime.
* gdalformat - is the output file format of the outCompImg, any GDAL compatable format is OK (Defaut is KEA).
* dataType - is the data type of the output image (outCompImg). If None is provided then the data type of the first input image will be used (Default None). 
* calcStats calculate image statics and pyramids (Default=True)
    """
    rsgisUtils = rsgislib.RSGISPyUtils()
    uidStr = rsgisUtils.uidGenerator()
    
    # Get List of input images:
    inImages = glob.glob(inImgsPattern)
    
    if len(inImages) > 1:
        tmpPresent = True
        if not os.path.exists(tmpPath):
            os.makedirs(tmpPath)
            tmpPresent = False 
        
        refLayersPath = os.path.join(tmpPath, 'RefLyrs_'+uidStr)
        
        refImgTmpPresent = True
        if not os.path.exists(refLayersPath):
            os.makedirs(refLayersPath)
            refImgTmpPresent = False
        
        if dataType is None:
            rsgisUtils.getRSGISLibDataTypeFromImg(inImages[0])
        
        numInLyrs = len(inImages)
        
        numpy.random.seed(5)
        red = numpy.random.randint(1, 255, numInLyrs+1, int)
        red[0] = 0
        numpy.random.seed(2)
        green = numpy.random.randint(1, 255, numInLyrs+1, int)
        green[0] = 0
        numpy.random.seed(9)
        blue = numpy.random.randint(1, 255, numInLyrs+1, int)
        blue[0] = 0
        alpha = numpy.zeros_like(blue)
        alpha[...] = 255
        imgLyrs = numpy.empty(numInLyrs+1, dtype=numpy.dtype('a255'))
            
        # Generate Comp Ref layers:
        landWaterMskBandDefns = []
        mskImgs = []
        idx = 1
        onlyLS8 = True
        incLS8 = False
        for img in inImages:
            print('In Image ('+str(idx) + '):\t' + img)
            imgLyrs[idx] = os.path.basename(img)
            baseImgName = os.path.splitext(os.path.basename(img))[0]
            refLyrNDVIImg = os.path.join(refLayersPath, baseImgName+'_ndvi.kea')
            refLyrNDWIImg = os.path.join(refLayersPath, baseImgName+'_ndwi.kea')
            if 'LS8' in img:
                rBand = 4
                nBand = 5
                sBand = 6
                incLS8 = True
            else:
                rBand = 3
                nBand = 4
                sBand = 5
                onlyLS8 = False
            
            rsgislib.imagecalc.calcindices.calcNDVI(img, rBand, nBand, refLyrNDVIImg, False)
            rsgislib.imagecalc.calcindices.calcNDWI(img, nBand, sBand, refLyrNDWIImg, False)
            
            refLyrMskImg = os.path.join(refLayersPath, baseImgName+'_waterLandMsk.kea')
            bandDefns = []
            bandDefns.append(rsgislib.imagecalc.BandDefn('ndvi', refLyrNDVIImg, 1))
            bandDefns.append(rsgislib.imagecalc.BandDefn('ndwi', refLyrNDWIImg, 1))
            rsgislib.imagecalc.bandMath(refLyrMskImg, 'ndvi<-1?0:ndvi>0.3?1:ndwi>0.01?2:1', 'KEA', rsgislib.TYPE_8UINT, bandDefns)
            mskImgs.append(refLyrMskImg)
            idx = idx + 1
        imgLyrs[0] = ""        
        
        refLyrMskStackImg = os.path.join(refLayersPath, uidStr+'_waterLandMskStack.kea')
        rsgislib.imageutils.stackImageBands(mskImgs, None, refLyrMskStackImg, -1, -1, 'KEA', rsgislib.TYPE_8UINT)
        rsgislib.imagecalc.imagePixelColumnSummary(refLyrMskStackImg, outMskImg, rsgislib.imagecalc.StatsSummary(calcMedian=True), 'KEA', rsgislib.TYPE_8UINT, 0, True)        
        rsgislib.rastergis.populateStats(outMskImg, True, True, True)
        
        idx = 1
        refLyrsLst = []
        for img in inImages:
            print('In Image ('+str(idx) + '):\t' + img)
            baseImgName = os.path.splitext(os.path.basename(img))[0]
            refLyrNDVIImg = os.path.join(refLayersPath, baseImgName+'_ndvi.kea')
            refLyrNDWIImg = os.path.join(refLayersPath, baseImgName+'_ndwi.kea')
            refLyrLclMskImg = os.path.join(refLayersPath, baseImgName+'_waterLandMsk.kea')
            
            refLyrImg = os.path.join(refLayersPath, baseImgName+'_refHybrid.kea')
            bandDefns = []
            bandDefns.append(rsgislib.imagecalc.BandDefn('lmsk', refLyrLclMskImg, 1))
            bandDefns.append(rsgislib.imagecalc.BandDefn('omsk', outMskImg, 1))
            bandDefns.append(rsgislib.imagecalc.BandDefn('ndvi', refLyrNDVIImg, 1))
            bandDefns.append(rsgislib.imagecalc.BandDefn('ndwi', refLyrNDWIImg, 1))
            rsgislib.imagecalc.bandMath(refLyrImg, 'lmsk==0?-999:omsk==1?ndvi:omsk==2?ndwi:-999', 'KEA', rsgislib.TYPE_32FLOAT, bandDefns)
            refLyrsLst.append(refLyrImg)
            idx = idx + 1
        
        if incLS8 and (not onlyLS8):
            inImagesTmp = []
            for img in inImages:
                if 'LS8' in img:
                    baseImgName = os.path.splitext(os.path.basename(img))[0]
                    reflSubImg = os.path.join(tmpPath, baseImgName+'_bandsub.kea')
                    rsgislib.imageutils.selectImageBands(img, reflSubImg, 'KEA', dataType, [2,3,4,5,6,7])
                    inImagesTmp.append(reflSubImg)
                else:
                    inImagesTmp.append(img)
            inImages = inImagesTmp
        
        # Create REF Image
        rsgislib.imagecalc.getImgIdxForStat(refLyrsLst, outRefImg, 'KEA', -999, rsgislib.SUMTYPE_MAX)
        if calcStats:
            # Pop Ref Image with stats
            rsgislib.rastergis.populateStats(outRefImg, True, True, True)
            
            # Open the clumps dataset as a gdal dataset
            ratDataset = osgeo.gdal.Open(outRefImg, osgeo.gdal.GA_Update)
            # Write colours to RAT
            rios.rat.writeColumn(ratDataset, "Red", red)
            rios.rat.writeColumn(ratDataset, "Green", green)
            rios.rat.writeColumn(ratDataset, "Blue", blue)
            rios.rat.writeColumn(ratDataset, "Alpha", alpha)
            rios.rat.writeColumn(ratDataset, "Image", imgLyrs)
            ratDataset = None
        
        # Create Composite Image
        rsgislib.imageutils.createRefImgCompositeImg(inImages, outCompImg, outRefImg, gdalformat, dataType, 0.0)
        
        if calcStats:
            # Calc Stats
            rsgislib.imageutils.popImageStats(outCompImg, usenodataval=True, nodataval=0, calcpyramids=True)
        
        if not refImgTmpPresent:
            shutil.rmtree(refLayersPath, ignore_errors=True)
    
        if not tmpPresent:
            shutil.rmtree(tmpPath, ignore_errors=True)

    elif len(inImages) == 1:
        print("Only 1 Input Image, Just Copying File to output")
        shutil.copy(inImages[0], outCompImg)
    else:
        raise rsgislib.RSGISPyException("There were no input images for " + inImgsPattern)

    
def createMaxNDVINDWIComposite(refImg, inImgsPattern, rBand, nBand, sBand, outRefImg, outCompImg, outMskImg, tmpPath='./tmp', gdalformat='KEA', dataType=None, calcStats=True, reprojmethod='cubic'):
    """
Create an image composite from multiple input images where the pixel brought through into the composite is the one with
the maximum NDVI over land and NDWI over water. A mask of land and water regions is also produced. The reference image is
used to define the spatial extent of the output images and spatial projection.

* refImg - is a reference image with any number of bands and data type which is used to define the output image extent and projection.
* inImgsPattern - is a pattern (ready for glob.glob(inImgsPattern)) so needs an * within the pattern to find the input image files.
* rBand - is an integer specifying the red band in the input images (starts at 1), used in the NDVI index.
* nBand - is an integer specifying the NIR band in the input images (starts at 1), used in the NDVI and NDWI index.
* sBand - is an integer specifying the SWIR band in the input images (starts at 1), used in the NDVI and NDWI index.
* outRefImg - is the output reference image which details which input image is forming the output image pixel value (Note. this file will always be a KEA file as RAT is used).
* outCompImg - is the output composite image for which gdalformat and dataType define the format and data type.
* outMskImg - is the output mask image for regions of water and land where ndvi vs ndwi are used (0=nodata, 1=land, 2=water)
* tmpPath - is a temp path for intemediate files, if this path doesn't exist is will be created and deleted at runtime.
* gdalformat - is the output file format of the outCompImg, any GDAL compatable format is OK (Defaut is KEA).
* dataType - is the data type of the output image (outCompImg). If None is provided then the data type of the first input image will be used (Default None). 
* calcStats - calculate image statics and pyramids (Default=True)
* reprojmethod - specifies the interpolation method used to reproject the input images which are in a different projection and/or pixel size as the reference image (default: cubic).
    """
    rsgisUtils = rsgislib.RSGISPyUtils()
    uidStr = rsgisUtils.uidGenerator()
    
    # Get List of input images:
    inImages = glob.glob(inImgsPattern)
    
    if len(inImages) > 1:
        init_in_images = inImages
        inImages = []
        inImagesReProj = []
        nBands = 0
        first = True
        for img in init_in_images:
            if first:
                nBands = rsgisUtils.getImageBandCount(img)
                first = False
            else:
                cBands = rsgisUtils.getImageBandCount(img)
                if cBands != nBands:
                    raise rsgislib.RSGISPyException("The number of image bands is not consistent (Bands: {0} and {1})".format(nBands, cBands))
            
            sameProj = rsgisUtils.doGDALLayersHaveSameProj(refImg, img)
            if rsgislib.imageutils.doImagesOverlap(refImg, img):
                if sameProj:
                    if rsgisUtils.doImageResMatch(refImg, img):
                        inImages.append(img)
                    else:
                        inImagesReProj.append(img)
                else:
                    inImagesReProj.append(img)
                    
        nImgs = len(inImages) + len(inImagesReProj)
        print("There are {} images with overlap to create the composite.".format(nImgs))
        if nImgs > 1:
            if dataType is None:
                if len(inImages) > 0:
                    dataType = rsgisUtils.getRSGISLibDataTypeFromImg(inImages[0])
                else:
                    dataType = rsgisUtils.getRSGISLibDataTypeFromImg(inImagesReProj[0])
        
            tmpPresent = True
            if not os.path.exists(tmpPath):
                os.makedirs(tmpPath)
                tmpPresent = False 
            
            reprojLayersPath = os.path.join(tmpPath, 'Reproj_'+uidStr)
            reprojImgTmpPresent = True
            if not os.path.exists(reprojLayersPath):
                os.makedirs(reprojLayersPath)
                reprojImgTmpPresent = False
                        
            for img in inImagesReProj:
                basename = os.path.splitext(os.path.basename(img))[0]
                outImg = os.path.join(reprojLayersPath, basename+"_reproj.kea")
                rsgislib.imageutils.resampleImage2Match(refImg, img, outImg, 'KEA', reprojmethod, dataType)
                inImages.append(outImg)
            
            refLayersPath = os.path.join(tmpPath, 'RefLyrs_'+uidStr)
            refImgTmpPresent = True
            if not os.path.exists(refLayersPath):
                os.makedirs(refLayersPath)
                refImgTmpPresent = False
                        
            numInLyrs = len(inImages)
            
            numpy.random.seed(5)
            red = numpy.random.randint(1, 255, numInLyrs+1, int)
            red[0] = 0
            numpy.random.seed(2)
            green = numpy.random.randint(1, 255, numInLyrs+1, int)
            green[0] = 0
            numpy.random.seed(9)
            blue = numpy.random.randint(1, 255, numInLyrs+1, int)
            blue[0] = 0
            alpha = numpy.zeros_like(blue)
            alpha[...] = 255
            imgLyrs = numpy.empty(numInLyrs+1, dtype=numpy.dtype('a255'))
                
            # Generate Comp Ref layers:
            landWaterMskBandDefns = []
            mskImgs = []
            idx = 1
            for img in inImages:
                print('In Image ('+str(idx) + '):\t' + img)
                imgLyrs[idx] = os.path.basename(img)
                baseImgName = os.path.splitext(os.path.basename(img))[0]
                refLyrNDVIImg = os.path.join(refLayersPath, baseImgName+'_ndvi.kea')
                refLyrNDWIImg = os.path.join(refLayersPath, baseImgName+'_ndwi.kea')
                rsgislib.imagecalc.calcindices.calcNDVI(img, rBand, nBand, refLyrNDVIImg, False)
                rsgislib.imagecalc.calcindices.calcNDWI(img, nBand, sBand, refLyrNDWIImg, False)
                
                refLyrMskImg = os.path.join(refLayersPath, baseImgName+'_waterLandMsk.kea')
                bandDefns = []
                bandDefns.append(rsgislib.imagecalc.BandDefn('ndvi', refLyrNDVIImg, 1))
                bandDefns.append(rsgislib.imagecalc.BandDefn('ndwi', refLyrNDWIImg, 1))
                rsgislib.imagecalc.bandMath(refLyrMskImg, 'ndvi<-1?0:ndvi>0.3?1:ndwi>0.01?2:1', 'KEA', rsgislib.TYPE_8UINT, bandDefns)
                mskImgs.append(refLyrMskImg)
                idx = idx + 1
            imgLyrs[0] = ""        
            
            refLyrMskStackImg = os.path.join(refLayersPath, uidStr+'_waterLandMskStack.kea')
            rsgislib.imageutils.stackImageBands(mskImgs, None, refLyrMskStackImg, -1, -1, 'KEA', rsgislib.TYPE_8UINT)
            rsgislib.imagecalc.imagePixelColumnSummary(refLyrMskStackImg, outMskImg, rsgislib.imagecalc.StatsSummary(calcMedian=True), 'KEA', rsgislib.TYPE_8UINT, 0, True)        
            rsgislib.rastergis.populateStats(outMskImg, True, True, True)
            
            idx = 1
            refLyrsLst = []
            for img in inImages:
                print('In Image ('+str(idx) + '):\t' + img)
                baseImgName = os.path.splitext(os.path.basename(img))[0]
                refLyrNDVIImg = os.path.join(refLayersPath, baseImgName+'_ndvi.kea')
                refLyrNDWIImg = os.path.join(refLayersPath, baseImgName+'_ndwi.kea')
                refLyrLclMskImg = os.path.join(refLayersPath, baseImgName+'_waterLandMsk.kea')
                
                refLyrImg = os.path.join(refLayersPath, baseImgName+'_refHybrid.kea')
                bandDefns = []
                bandDefns.append(rsgislib.imagecalc.BandDefn('lmsk', refLyrLclMskImg, 1))
                bandDefns.append(rsgislib.imagecalc.BandDefn('omsk', outMskImg, 1))
                bandDefns.append(rsgislib.imagecalc.BandDefn('ndvi', refLyrNDVIImg, 1))
                bandDefns.append(rsgislib.imagecalc.BandDefn('ndwi', refLyrNDWIImg, 1))
                rsgislib.imagecalc.bandMath(refLyrImg, 'lmsk==0?-999:omsk==1?ndvi:omsk==2?ndwi:-999', 'KEA', rsgislib.TYPE_32FLOAT, bandDefns)
                refLyrsLst.append(refLyrImg)
                idx = idx + 1
            
            # Create REF Image
            rsgislib.imagecalc.getImgIdxForStat(refLyrsLst, outRefImg, 'KEA', -999, rsgislib.SUMTYPE_MAX)
            if calcStats:
                # Pop Ref Image with stats
                rsgislib.rastergis.populateStats(outRefImg, True, True, True)
                
                # Open the clumps dataset as a gdal dataset
                ratDataset = osgeo.gdal.Open(outRefImg, osgeo.gdal.GA_Update)
                # Write colours to RAT
                rios.rat.writeColumn(ratDataset, "Red", red)
                rios.rat.writeColumn(ratDataset, "Green", green)
                rios.rat.writeColumn(ratDataset, "Blue", blue)
                rios.rat.writeColumn(ratDataset, "Alpha", alpha)
                rios.rat.writeColumn(ratDataset, "Image", imgLyrs)
                ratDataset = None
            
            # Create Composite Image
            rsgislib.imageutils.createRefImgCompositeImg(inImages, outCompImg, outRefImg, gdalformat, dataType, 0.0)
            
            if calcStats:
                # Calc Stats
                rsgislib.imageutils.popImageStats(outCompImg, usenodataval=True, nodataval=0, calcpyramids=True)
            
            if not refImgTmpPresent:
                shutil.rmtree(refLayersPath, ignore_errors=True)
                
            if not reprojImgTmpPresent:
                shutil.rmtree(reprojLayersPath, ignore_errors=True)            
        
            if not tmpPresent:
                shutil.rmtree(tmpPath, ignore_errors=True)
        else:
            raise rsgislib.RSGISPyException("There were only {0} images which intersect with the reference image.".format(nImgs))

    elif len(inImages) == 1:
        print("Only 1 Input Image, Just Copying File to output")
        shutil.copy(inImages[0], outCompImg)
    else:
        raise rsgislib.RSGISPyException("There were no input images for " + inImgsPattern)



