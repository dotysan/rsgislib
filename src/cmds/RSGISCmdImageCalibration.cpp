/*
 *  RSGISCmdImageCalibration.cpp
 *
 *
 *  Created by Pete Bunting on 10/07/2013.
 *  Copyright 2013 RSGISLib.
 *
 *  RSGISLib is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  RSGISLib is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with RSGISLib.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

#include "RSGISCmdImageCalibration.h"
#include "RSGISCmdParent.h"

#include "calibration/RSGISStandardDN2RadianceCalibration.h"
#include "calibration/RSGISCalculateTopOfAtmosphereReflectance.h"
#include "calibration/RSGISApply6SCoefficients.h"
#include "calibration/RSGISApplySubtractOffsets.h"
#include "calibration/RSGISCloudMasking.h"
#include "calibration/RSGISHydroDEMFillSoilleGratin94.h"

#include "img/RSGISImageCalcException.h"
#include "img/RSGISCalcImageValue.h"
#include "img/RSGISCalcImage.h"
#include "img/RSGISImageUtils.h"
#include "img/RSGISCalcEditImage.h"
#include "img/RSGISCopyImage.h"

#include "rastergis/RSGISCalcImageStatsAndPyramids.h"
#include "rastergis/RSGISPopRATWithStats.h"
#include "rastergis/RSGISRasterAttUtils.h"

namespace rsgis{ namespace cmds {
    
    void executeConvertLandsat2Radiance(std::string outputImage, std::string gdalFormat, std::vector<CmdsLandsatRadianceGainsOffsets> landsatRadGainOffs)throw(RSGISCmdException)
    {
        GDALAllRegister();
        
        try
        {
            unsigned int numBands = landsatRadGainOffs.size();
            GDALDataset **datasets = new GDALDataset*[numBands];
            std::string *outBandNames = new std::string[numBands];
            
            rsgis::calib::LandsatRadianceGainsOffsets *lsRadGainOffs = new rsgis::calib::LandsatRadianceGainsOffsets[numBands];
            
            unsigned int i = 0;
            unsigned int numRasterBands = 0;
            unsigned int totalNumRasterBands = 0;
            for(std::vector<rsgis::cmds::CmdsLandsatRadianceGainsOffsets>::iterator iterBands = landsatRadGainOffs.begin(); iterBands != landsatRadGainOffs.end(); ++iterBands)
			{
                std::cout << "Opening: " << (*iterBands).imagePath << std::endl;
                
                datasets[i] = (GDALDataset *) GDALOpen((*iterBands).imagePath.c_str(), GA_ReadOnly);
                if(datasets[i] == NULL)
                {
                    std::string message = std::string("Could not open image ") + (*iterBands).imagePath;
                    throw RSGISImageException(message.c_str());
                }
                
                numRasterBands = datasets[i]->GetRasterCount();
                
                if((*iterBands).band > numRasterBands)
                {
                    throw RSGISImageException("You have specified a band which is not within the image");
                }
                lsRadGainOffs[i].band = totalNumRasterBands + (*iterBands).band-1;
                
                lsRadGainOffs[i].lMax = (*iterBands).lMax;
                lsRadGainOffs[i].lMin = (*iterBands).lMin;
                lsRadGainOffs[i].qCalMax = (*iterBands).qCalMax;
                lsRadGainOffs[i].qCalMin = (*iterBands).qCalMin;
                
                outBandNames[i] = (*iterBands).bandName;
                
                totalNumRasterBands += numRasterBands;
                ++i;
			}
            
            rsgis::calib::RSGISLandsatRadianceCalibration *radianceCalibration = new rsgis::calib::RSGISLandsatRadianceCalibration(numBands, lsRadGainOffs);
            rsgis::img::RSGISCalcImage *calcImage = new rsgis::img::RSGISCalcImage(radianceCalibration, "", true);
 
            calcImage->calcImage(datasets, numBands, outputImage, true, outBandNames, gdalFormat);
            
            for(unsigned int i = 0; i < numBands; ++i)
            {
                GDALClose(datasets[i]);
            }
            
            delete[] datasets;
            delete[] lsRadGainOffs;
            delete[] outBandNames;
            
            delete radianceCalibration;
            delete calcImage;
        }
        catch(RSGISException &e)
        {
            throw RSGISCmdException(e.what());
        }
        catch(std::exception &e)
        {
            throw RSGISCmdException(e.what());
        }
    }
    
    void executeConvertLandsat2RadianceMultiAdd(std::string outputImage, std::string gdalFormat, std::vector<CmdsLandsatRadianceGainsOffsetsMultiAdd> landsatRadGainOffs)throw(RSGISCmdException)
    {
        GDALAllRegister();
        
        try
        {
            unsigned int numBands = landsatRadGainOffs.size();
            GDALDataset **datasets = new GDALDataset*[numBands];
            std::string *outBandNames = new std::string[numBands];
            
            rsgis::calib::LandsatRadianceGainsOffsetsMultiAdd *lsRadGainOffs = new rsgis::calib::LandsatRadianceGainsOffsetsMultiAdd[numBands];
            
            unsigned int i = 0;
            unsigned int numRasterBands = 0;
            unsigned int totalNumRasterBands = 0;
            for(std::vector<rsgis::cmds::CmdsLandsatRadianceGainsOffsetsMultiAdd>::iterator iterBands = landsatRadGainOffs.begin(); iterBands != landsatRadGainOffs.end(); ++iterBands)
			{
                std::cout << "Opening: " << (*iterBands).imagePath << std::endl;
                
                datasets[i] = (GDALDataset *) GDALOpen((*iterBands).imagePath.c_str(), GA_ReadOnly);
                if(datasets[i] == NULL)
                {
                    std::string message = std::string("Could not open image ") + (*iterBands).imagePath;
                    throw RSGISImageException(message.c_str());
                }
                
                numRasterBands = datasets[i]->GetRasterCount();
                
                if((*iterBands).band > numRasterBands)
                {
                    throw RSGISImageException("You have specified a band which is not within the image");
                }
                lsRadGainOffs[i].band = totalNumRasterBands + (*iterBands).band-1;
                
                lsRadGainOffs[i].addVal = (*iterBands).addVal;
                lsRadGainOffs[i].multiVal = (*iterBands).multiVal;
                
                outBandNames[i] = (*iterBands).bandName;
                
                totalNumRasterBands += numRasterBands;
                ++i;
			}
            
            rsgis::calib::RSGISLandsatRadianceCalibrationMultiAdd *radianceCalibration = new rsgis::calib::RSGISLandsatRadianceCalibrationMultiAdd(numBands, lsRadGainOffs);
            rsgis::img::RSGISCalcImage *calcImage = new rsgis::img::RSGISCalcImage(radianceCalibration, "", true);
            
            calcImage->calcImage(datasets, numBands, outputImage, true, outBandNames, gdalFormat);
            
            for(unsigned int i = 0; i < numBands; ++i)
            {
                GDALClose(datasets[i]);
            }
            
            delete[] datasets;
            delete[] lsRadGainOffs;
            delete[] outBandNames;
            
            delete radianceCalibration;
            delete calcImage;
        }
        catch(RSGISException &e)
        {
            throw RSGISCmdException(e.what());
        }
        catch(std::exception &e)
        {
            throw RSGISCmdException(e.what());
        }
    }
    
    void executeConvertRadiance2TOARefl(std::string inputImage, std::string outputImage, std::string gdalFormat, rsgis::RSGISLibDataType rsgisOutDataType, float scaleFactor, unsigned int julianDay, bool useJulianDay, unsigned int year, unsigned int month, unsigned int day, float solarZenith, float *solarIrradiance, unsigned int numBands) throw(RSGISCmdException)
    {
        GDALAllRegister();
        GDALDataset **datasets = NULL;
        rsgis::calib::RSGISCalculateTopOfAtmosphereReflectance *calcTopAtmosRefl = NULL;
        rsgis::img::RSGISCalcImage *calcImage = NULL;
        
        try
        {
            datasets = new GDALDataset*[1];
            
            std::cout << "Open " << inputImage << std::endl;
            datasets[0] = (GDALDataset *) GDALOpen(inputImage.c_str(), GA_ReadOnly);
            if(datasets[0] == NULL)
            {
                std::string message = std::string("Could not open image ") + inputImage;
                throw rsgis::RSGISImageException(message.c_str());
            }
            
            unsigned int numRasterBands = datasets[0]->GetRasterCount();
            if(numBands != numRasterBands)
            {
                GDALClose(datasets[0]);
                delete[] datasets;
                throw rsgis::RSGISException("The number of input image bands and solar irradiance values are different.");
            }
            
            double solarDistance = 0;
            
            if(!useJulianDay)
            {
                julianDay = rsgis::calib::rsgisGetJulianDay(day, month, year);
                //std::cout << "Julian Day = " << julianDay << std::endl;
            }
            
            solarDistance = rsgis::calib::rsgisCalcSolarDistance(julianDay);
            //std::cout << "Solar Dist = " << solarDistance << std::endl;
            //std::cout << "Solar Zenith = " << solarZenith << std::endl;
            
            calcTopAtmosRefl = new rsgis::calib::RSGISCalculateTopOfAtmosphereReflectance(numRasterBands, solarIrradiance, solarDistance, solarZenith, scaleFactor);
            
            calcImage = new rsgis::img::RSGISCalcImage(calcTopAtmosRefl, "", true);
            calcImage->calcImage(datasets, 1, outputImage, false, NULL, gdalFormat, RSGIS_to_GDAL_Type(rsgisOutDataType));
            
            GDALClose(datasets[0]);
            delete[] datasets;
            
            delete calcTopAtmosRefl;
            delete calcImage;
        }
        catch(RSGISException &e)
        {
            throw RSGISCmdException(e.what());
        }
        catch(std::exception &e)
        {
            throw RSGISCmdException(e.what());
        }
    }
    
    void executeRad2SREFSingle6sParams(std::string inputImage, std::string outputImage, std::string gdalFormat, rsgis::RSGISLibDataType rsgisOutDataType, float scaleFactor, unsigned int *imageBands, float *aX, float *bX, float *cX, int numValues, float noDataVal, bool useNoDataVal)throw(RSGISCmdException)
    {
        try
        {
            GDALAllRegister();
            GDALDataset **datasets = new GDALDataset*[1];
            std::cout << "Open image" << inputImage << std::endl;
            datasets[0] = (GDALDataset *) GDALOpen(inputImage.c_str(), GA_ReadOnly);
            if(datasets[0] == NULL)
            {
                std::string message = std::string("Could not open image ") + inputImage;
                throw rsgis::RSGISImageException(message.c_str());
            }
            
            int numRasterBands = datasets[0]->GetRasterCount();
            if(numValues != numRasterBands)
            {
                GDALClose(datasets[0]);
                delete[] datasets;
                throw rsgis::RSGISException("The number of input image bands is not equal to the number coefficients provided.");
            }
            
            for(int i = 0; i < numValues; ++i)
            {
                imageBands[i] -= 1;
            }
            
            rsgis::calib::RSGISApply6SCoefficientsSingleParam *apply6SCoefficients = new rsgis::calib::RSGISApply6SCoefficientsSingleParam(imageBands, aX, bX, cX, numValues, noDataVal, useNoDataVal, scaleFactor);
            
            rsgis::img::RSGISCalcImage *calcImage = new rsgis::img::RSGISCalcImage(apply6SCoefficients, "", true);
            calcImage->calcImage(datasets, 1, outputImage, false, NULL, gdalFormat, RSGIS_to_GDAL_Type(rsgisOutDataType));
            
            delete apply6SCoefficients;
            delete calcImage;
            
            GDALClose(datasets[0]);
            delete[] datasets;            
        }
        catch(rsgis::RSGISException &e)
        {
            throw RSGISCmdException(e.what());
        }
        catch(std::exception &e)
        {
            throw RSGISCmdException(e.what());
        }
        
    }
                
    void executeRad2SREFElevLUT6sParams(std::string inputRadImage, std::string inputDEM, std::string outputImage, std::string gdalFormat, rsgis::RSGISLibDataType rsgisOutDataType, float scaleFactor, std::vector<Cmds6SElevationLUT> *lut, float noDataVal, bool useNoDataVal)throw(RSGISCmdException)
    {
        try
        {
            GDALAllRegister();
            GDALDataset **datasets = new GDALDataset*[2];
            std::cout << "Open DEM image: \'" << inputDEM << "\'" << std::endl;
            datasets[0] = (GDALDataset *) GDALOpen(inputDEM.c_str(), GA_ReadOnly);
            if(datasets[0] == NULL)
            {
                std::string message = std::string("Could not open image ") + inputDEM;
                throw rsgis::RSGISImageException(message.c_str());
            }
            
            std::cout << "Open Radiance image: \'" << inputRadImage << "\'" << std::endl;
            datasets[1] = (GDALDataset *) GDALOpen(inputRadImage.c_str(), GA_ReadOnly);
            if(datasets[1] == NULL)
            {
                std::string message = std::string("Could not open image ") + inputRadImage;
                throw rsgis::RSGISImageException(message.c_str());
            }
            
            int numRasterBands = datasets[1]->GetRasterCount();
            
            std::vector<rsgis::calib::LUT6SElevation> *rsgisLUT = new std::vector<rsgis::calib::LUT6SElevation>();
            
            for(std::vector<Cmds6SElevationLUT>::iterator iterLUT = lut->begin(); iterLUT != lut->end(); ++iterLUT)
            {
                rsgis::calib::LUT6SElevation lutVal = rsgis::calib::LUT6SElevation();
                std::cout << "Elevation: " << (*iterLUT).elev << std::endl;
                
                lutVal.numValues = (*iterLUT).numValues;
                lutVal.elev = (*iterLUT).elev;
                lutVal.imageBands = new unsigned int[lutVal.numValues];
                lutVal.aX = new float[lutVal.numValues];
                lutVal.bX = new float[lutVal.numValues];
                lutVal.cX = new float[lutVal.numValues];
                
                
                for(unsigned int i = 0; i < (*iterLUT).numValues; ++i)
                {
                    if((*iterLUT).imageBands[i] > numRasterBands)
                    {
                        GDALClose(datasets[0]);
                        GDALClose(datasets[1]);
                        delete[] datasets;
                        throw rsgis::RSGISException("The number of input image bands is not equal to the number coefficients provided.");
                    }
                    lutVal.imageBands[i] = (*iterLUT).imageBands[i];
                    lutVal.aX[i] = (*iterLUT).aX[i];
                    lutVal.bX[i] = (*iterLUT).bX[i];
                    lutVal.cX[i] = (*iterLUT).cX[i];
                    std::cout << "\tBand " << lutVal.imageBands[i] << ": aX = " << lutVal.aX[i] << " bX = " << lutVal.bX[i] << " cX = " << lutVal.cX[i] << std::endl;
                }
                
                rsgisLUT->push_back(lutVal);
            }
            
            std::cout << "Apply Coefficients to input image...\n";

            rsgis::calib::RSGISApply6SCoefficientsElevLUTParam *apply6SCoefficients = new rsgis::calib::RSGISApply6SCoefficientsElevLUTParam(numRasterBands, rsgisLUT, noDataVal, useNoDataVal, scaleFactor);
            
            rsgis::img::RSGISCalcImage *calcImage = new rsgis::img::RSGISCalcImage(apply6SCoefficients, "", true);
            calcImage->calcImage(datasets, 2, outputImage, false, NULL, gdalFormat, RSGIS_to_GDAL_Type(rsgisOutDataType));
            
            delete apply6SCoefficients;
            delete calcImage;
            
            for(std::vector<rsgis::calib::LUT6SElevation>::iterator iterLUT = rsgisLUT->begin(); iterLUT != rsgisLUT->end(); ++iterLUT)
            {
                delete[] (*iterLUT).imageBands;
                delete[] (*iterLUT).aX;
                delete[] (*iterLUT).bX;
                delete[] (*iterLUT).cX;
            }
            delete rsgisLUT;
            
            GDALClose(datasets[0]);
            GDALClose(datasets[1]);
            delete[] datasets;
        }
        catch(rsgis::RSGISException &e)
        {
            throw RSGISCmdException(e.what());
        }
        catch(std::exception &e)
        {
            throw RSGISCmdException(e.what());
        }
    }
                
    void executeRad2SREFElevAOTLUT6sParams(std::string inputRadImage, std::string inputDEM, std::string inputAOTImg, std::string outputImage, std::string gdalFormat, rsgis::RSGISLibDataType rsgisOutDataType, float scaleFactor, std::vector<Cmds6SBaseElevAOTLUT> *lut, float noDataVal, bool useNoDataVal)throw(RSGISCmdException)
    {
        try
        {
            GDALAllRegister();
            GDALDataset **datasets = new GDALDataset*[3];
            std::cout << "Open DEM image: \'" << inputDEM << "\'" << std::endl;
            datasets[0] = (GDALDataset *) GDALOpen(inputDEM.c_str(), GA_ReadOnly);
            if(datasets[0] == NULL)
            {
                std::string message = std::string("Could not open image ") + inputDEM;
                throw rsgis::RSGISImageException(message.c_str());
            }
            
            std::cout << "Open AOT image: \'" << inputAOTImg << "\'" << std::endl;
            datasets[1] = (GDALDataset *) GDALOpen(inputAOTImg.c_str(), GA_ReadOnly);
            if(datasets[1] == NULL)
            {
                std::string message = std::string("Could not open image ") + inputAOTImg;
                throw rsgis::RSGISImageException(message.c_str());
            }
            
            std::cout << "Open Radiance image: \'" << inputRadImage << "\'" << std::endl;
            datasets[2] = (GDALDataset *) GDALOpen(inputRadImage.c_str(), GA_ReadOnly);
            if(datasets[2] == NULL)
            {
                std::string message = std::string("Could not open image ") + inputRadImage;
                throw rsgis::RSGISImageException(message.c_str());
            }
            
            int numRasterBands = datasets[2]->GetRasterCount();
            
            std::vector<rsgis::calib::LUT6SBaseElevAOT> *rsgisLUT = new std::vector<rsgis::calib::LUT6SBaseElevAOT>();
            
            for(std::vector<Cmds6SBaseElevAOTLUT>::iterator iterElevLUT = lut->begin(); iterElevLUT != lut->end(); ++iterElevLUT)
            {
                rsgis::calib::LUT6SBaseElevAOT lutElevVal = rsgis::calib::LUT6SBaseElevAOT();
                std::cout << "Elevation: " << (*iterElevLUT).elev << std::endl;
                lutElevVal.aotLUT = std::vector<rsgis::calib::LUT6SAOT>();
                lutElevVal.aotLUT.reserve((*iterElevLUT).aotLUT.size());
                
                for(std::vector<Cmds6SAOTLUT>::iterator iterAOTLUT = (*iterElevLUT).aotLUT.begin(); iterAOTLUT != (*iterElevLUT).aotLUT.end(); ++iterAOTLUT)
                {
                    rsgis::calib::LUT6SAOT aotLUTVal = rsgis::calib::LUT6SAOT();
                    aotLUTVal.aot = (*iterAOTLUT).aot;
                    aotLUTVal.numValues = (*iterAOTLUT).numValues;
                    aotLUTVal.imageBands = new unsigned int[aotLUTVal.numValues];
                    aotLUTVal.aX = new float[aotLUTVal.numValues];
                    aotLUTVal.bX = new float[aotLUTVal.numValues];
                    aotLUTVal.cX = new float[aotLUTVal.numValues];
                    
                    std::cout << "\tAOT: " << (*iterAOTLUT).aot << std::endl;
                    for(unsigned int i = 0; i < (*iterAOTLUT).numValues; ++i)
                    {
                        if((*iterAOTLUT).imageBands[i] > numRasterBands)
                        {
                            GDALClose(datasets[0]);
                            GDALClose(datasets[1]);
                            GDALClose(datasets[2]);
                            delete[] datasets;
                            throw rsgis::RSGISException("The number of input image bands is not equal to the number coefficients provided.");
                        }
                        aotLUTVal.imageBands[i] = (*iterAOTLUT).imageBands[i]+1;
                        aotLUTVal.aX[i] = (*iterAOTLUT).aX[i];
                        aotLUTVal.bX[i] = (*iterAOTLUT).bX[i];
                        aotLUTVal.cX[i] = (*iterAOTLUT).cX[i];
                        std::cout << "\t\tBand " << aotLUTVal.imageBands[i] << ": aX = " << aotLUTVal.aX[i] << " bX = " << aotLUTVal.bX[i] << " cX = " << aotLUTVal.cX[i] << std::endl;
                    }
                    
                    lutElevVal.aotLUT.push_back(aotLUTVal);
                }
                lutElevVal.elev = (*iterElevLUT).elev;
                
                rsgisLUT->push_back(lutElevVal);
            }
            
            std::cout << "Apply Coefficients to input image...\n";
            
            rsgis::calib::RSGISApply6SCoefficientsElevAOTLUTParam *apply6SCoefficients = new rsgis::calib::RSGISApply6SCoefficientsElevAOTLUTParam(numRasterBands, rsgisLUT, noDataVal, useNoDataVal, scaleFactor);
            
            rsgis::img::RSGISCalcImage *calcImage = new rsgis::img::RSGISCalcImage(apply6SCoefficients, "", true);
            calcImage->calcImage(datasets, 3, outputImage, false, NULL, gdalFormat, RSGIS_to_GDAL_Type(rsgisOutDataType));
            
            delete apply6SCoefficients;
            delete calcImage;
            
            for(std::vector<rsgis::calib::LUT6SBaseElevAOT>::iterator iterLUT = rsgisLUT->begin(); iterLUT != rsgisLUT->end(); ++iterLUT)
            {
                for(std::vector<rsgis::calib::LUT6SAOT>::iterator iterAOTLUT = (*iterLUT).aotLUT.begin(); iterAOTLUT != (*iterLUT).aotLUT.end(); ++iterAOTLUT)
                {
                    delete[] (*iterAOTLUT).imageBands;
                    delete[] (*iterAOTLUT).aX;
                    delete[] (*iterAOTLUT).bX;
                    delete[] (*iterAOTLUT).cX;
                }
            }
            delete rsgisLUT;
            
            GDALClose(datasets[0]);
            GDALClose(datasets[1]);
            GDALClose(datasets[2]);
            delete[] datasets;
        }
        catch(rsgis::RSGISException &e)
        {
            throw RSGISCmdException(e.what());
        }
        catch(std::exception &e)
        {
            throw RSGISCmdException(e.what());
        }
    }
                
    void executeApplySubtractOffsets(std::string inputImage, std::string outputImage, std::string offsetImage, bool nonNegative, std::string gdalFormat, rsgis::RSGISLibDataType rsgisOutDataType, float noDataVal, bool useNoDataVal, float darkObjReflVal) throw(RSGISCmdException)
    {
        try
        {
            GDALAllRegister();
            GDALDataset **datasets = new GDALDataset*[2];
            
            std::cout << "Open input image: \'" << inputImage << "\'" << std::endl;
            datasets[0] = (GDALDataset *) GDALOpen(inputImage.c_str(), GA_ReadOnly);
            if(datasets[0] == NULL)
            {
                std::string message = std::string("Could not open image ") + inputImage;
                throw rsgis::RSGISImageException(message.c_str());
            }
            
            std::cout << "Open Offset image: \'" << offsetImage << "\'" << std::endl;
            datasets[1] = (GDALDataset *) GDALOpen(offsetImage.c_str(), GA_ReadOnly);
            if(datasets[1] == NULL)
            {
                std::string message = std::string("Could not open image ") + offsetImage;
                throw rsgis::RSGISImageException(message.c_str());
            }
            
            if(datasets[0]->GetRasterCount() != datasets[1]->GetRasterCount())
            {
                throw rsgis::RSGISImageException("The two input images need to have the same number of image bands.");
            }
            int numRasterBands = datasets[0]->GetRasterCount();
            
            std::cout << "Apply offsets to input image...\n";
            
            rsgis::calib::RSGISApplyDarkObjSubtractOffsets *applyOffsets = new rsgis::calib::RSGISApplyDarkObjSubtractOffsets(numRasterBands, nonNegative, noDataVal, useNoDataVal, darkObjReflVal);
            
            rsgis::img::RSGISCalcImage *calcImage = new rsgis::img::RSGISCalcImage(applyOffsets, "", true);
            calcImage->calcImage(datasets, 2, outputImage, false, NULL, gdalFormat, RSGIS_to_GDAL_Type(rsgisOutDataType));
            
            delete applyOffsets;
            delete calcImage;
            
            GDALClose(datasets[0]);
            GDALClose(datasets[1]);
            delete[] datasets;
        }
        catch(rsgis::RSGISException &e)
        {
            throw RSGISCmdException(e.what());
        }
        catch(std::exception &e)
        {
            throw RSGISCmdException(e.what());
        }
    }
                
    void executeLandsatThermalRad2ThermalBrightness(std::string inputImage, std::string outputImage, std::string gdalFormat, rsgis::RSGISLibDataType rsgisOutDataType, float scaleFactor, std::vector<CmdsLandsatThermalCoeffs> landsatThermalCoeffs) throw(RSGISCmdException)
    {
        GDALAllRegister();
        try
        {
            unsigned int numBands = landsatThermalCoeffs.size();
            
            std::cout << "Opening: " << inputImage << std::endl;
            GDALDataset *dataset = (GDALDataset *) GDALOpen(inputImage.c_str(), GA_ReadOnly);
            if(dataset == NULL)
            {
                std::string message = std::string("Could not open image ") + inputImage;
                throw RSGISImageException(message.c_str());
            }
            unsigned int numRasterBands = dataset->GetRasterCount();
            
            std::string *outBandNames = new std::string[numRasterBands];
            float *k1 = new float[numRasterBands];
            float *k2 = new float[numRasterBands];
            
            unsigned int i = 0;
            for(std::vector<rsgis::cmds::CmdsLandsatThermalCoeffs>::iterator iterBands = landsatThermalCoeffs.begin(); iterBands != landsatThermalCoeffs.end(); ++iterBands)
			{
                if((*iterBands).band != (i+1))
                {
                    throw RSGISImageException("The bands must be specified in order.");
                }
                
                if((*iterBands).band > numRasterBands)
                {
                    throw RSGISImageException("You have specified a band which is not within the image");
                }
                
                k1[i] = (*iterBands).k1;
                k2[i] = (*iterBands).k2;
                outBandNames[i] = (*iterBands).bandName;
                
                ++i;
			}
            
            rsgis::calib::RSGISCalculateTOAThermalBrightness *calibLandsatThermalTOA = new rsgis::calib::RSGISCalculateTOAThermalBrightness(numBands, k1, k2, scaleFactor);
            rsgis::img::RSGISCalcImage *calcImage = new rsgis::img::RSGISCalcImage(calibLandsatThermalTOA, "", true);
            
            calcImage->calcImage(&dataset, 1, outputImage, true, outBandNames, gdalFormat, RSGIS_to_GDAL_Type(rsgisOutDataType));
            
            
            GDALClose(dataset);
            delete[] k1;
            delete[] k2;
            delete[] outBandNames;
            
            delete calibLandsatThermalTOA;
            delete calcImage;
        }
        catch(RSGISException &e)
        {
            throw RSGISCmdException(e.what());
        }
        catch(std::exception &e)
        {
            throw RSGISCmdException(e.what());
        }
    }
                
    void executeGenerateSaturationMask(std::string outputImage, std::string gdalFormat, std::vector<CmdsSaturatedPixel> imgBandInfo)throw(RSGISCmdException)
    {
        GDALAllRegister();
        try
        {
            unsigned int numBands = imgBandInfo.size();
            GDALDataset **datasets = new GDALDataset*[numBands];
            std::string *outBandNames = new std::string[numBands];
            
            rsgis::calib::RSGISSaturatedPixelInfo *satBandPxlInfo = new rsgis::calib::RSGISSaturatedPixelInfo[numBands];
            
            unsigned int i = 0;
            unsigned int numRasterBands = 0;
            unsigned int totalNumRasterBands = 0;
            for(std::vector<rsgis::cmds::CmdsSaturatedPixel>::iterator iterBands = imgBandInfo.begin(); iterBands != imgBandInfo.end(); ++iterBands)
			{
                std::cout << "Opening: " << (*iterBands).imagePath << std::endl;
                
                datasets[i] = (GDALDataset *) GDALOpen((*iterBands).imagePath.c_str(), GA_ReadOnly);
                if(datasets[i] == NULL)
                {
                    std::string message = std::string("Could not open image ") + (*iterBands).imagePath;
                    throw RSGISImageException(message.c_str());
                }
                
                numRasterBands = datasets[i]->GetRasterCount();
                
                if((*iterBands).band > numRasterBands)
                {
                    throw RSGISImageException("You have specified a band which is not within the image");
                }
                satBandPxlInfo[i].band = totalNumRasterBands + (*iterBands).band-1;
                satBandPxlInfo[i].satVal = (*iterBands).satVal;
                outBandNames[i] = (*iterBands).bandName;
                
                totalNumRasterBands += numRasterBands;
                ++i;
			}
            
            rsgis::calib::RSGISIdentifySaturatePixels *createSatPxlMask = new rsgis::calib::RSGISIdentifySaturatePixels(numBands, satBandPxlInfo);
            rsgis::img::RSGISCalcImage *calcImage = new rsgis::img::RSGISCalcImage(createSatPxlMask, "", true);
            
            calcImage->calcImage(datasets, numBands, outputImage, true, outBandNames, gdalFormat, GDT_Byte);
            
            for(unsigned int i = 0; i < numBands; ++i)
            {
                GDALClose(datasets[i]);
            }
            
            delete[] datasets;
            delete[] satBandPxlInfo;
            delete[] outBandNames;
            
            delete createSatPxlMask;
            delete calcImage;
        }
        catch(RSGISException &e)
        {
            throw RSGISCmdException(e.what());
        }
        catch(std::exception &e)
        {
            throw RSGISCmdException(e.what());
        }
    }
    
    void executeLandsatTMCloudFMask(std::string inputTOAImage, std::string inputThermalImage, std::string inputSaturateImage, std::string validImg, std::string outputImage, std::string pass1TmpOutImage, std::string landWaterTmpOutImage, std::string cloudLandProbTmpOutImage, std::string tmpNIRBandImg, std::string tmpNIRFillBandImg, std::string tmpPotentClouds, std::string gdalFormat, float scaleFactorIn) throw(RSGISCmdException)
    {
        GDALAllRegister();
        try
        {
            rsgis::img::RSGISImageUtils imgUtils;
            rsgis::rastergis::RSGISRasterAttUtils ratUtils;
            rsgis::rastergis::RSGISPopRATWithStats calcClumpStats;
            
            GDALDataset **datasets = NULL;
            std::cout << "Opening: " << inputTOAImage << std::endl;
            GDALDataset *reflDataset = (GDALDataset *) GDALOpen(inputTOAImage.c_str(), GA_ReadOnly);
            if(reflDataset == NULL)
            {
                std::string message = std::string("Could not open image ") + inputTOAImage;
                throw RSGISImageException(message.c_str());
            }
            unsigned int numReflBands = reflDataset->GetRasterCount();
            
            
            GDALDataType imgReflDT = reflDataset->GetRasterBand(1)->GetRasterDataType();
            if((imgReflDT == GDT_Float32) | (imgReflDT == GDT_Float64) | (imgReflDT == GDT_Unknown) | (imgReflDT == GDT_CInt16) | (imgReflDT == GDT_CInt32) | (imgReflDT == GDT_CFloat32) | (imgReflDT == GDT_CFloat64))
            {
                throw rsgis::RSGISImageException("Input TOA image must be of an integer data type.");
            }
            
            
            std::cout << "Opening: " << inputThermalImage << std::endl;
            GDALDataset *thermDataset = (GDALDataset *) GDALOpen(inputThermalImage.c_str(), GA_ReadOnly);
            if(thermDataset == NULL)
            {
                std::string message = std::string("Could not open image ") + inputThermalImage;
                throw RSGISImageException(message.c_str());
            }
            unsigned int numThermBands = thermDataset->GetRasterCount();
            
            std::cout << "Opening: " << inputSaturateImage << std::endl;
            GDALDataset *saturateDataset = (GDALDataset *) GDALOpen(inputSaturateImage.c_str(), GA_ReadOnly);
            if(saturateDataset == NULL)
            {
                std::string message = std::string("Could not open image ") + inputSaturateImage;
                throw RSGISImageException(message.c_str());
            }
            unsigned int numSaturateBands = saturateDataset->GetRasterCount();
            
            std::cout << "Opening: " << validImg << std::endl;
            GDALDataset *validAreaDataset = (GDALDataset *) GDALOpen(validImg.c_str(), GA_ReadOnly);
            if(validAreaDataset == NULL)
            {
                std::string message = std::string("Could not open image ") + validImg;
                throw RSGISImageException(message.c_str());
            }
            
            if((numReflBands+numThermBands) != numSaturateBands)
            {
                throw RSGISImageException("The number of saturation bands is not equal to the number of refl and thermal bands.");
                
                GDALClose(reflDataset);
                GDALClose(thermDataset);
                GDALClose(saturateDataset);
                GDALClose(validAreaDataset);
            }
            rsgis::rastergis::RSGISPopulateWithImageStats popImageStats;
            
            std::cout << "Apply first pass FMask to classifiy initial clear sky regions...\n";
            rsgis::calib::RSGISLandsatFMaskPass1CloudMasking cloudMaskPass1 = rsgis::calib::RSGISLandsatFMaskPass1CloudMasking(scaleFactorIn, (numReflBands+numThermBands));
            rsgis::img::RSGISCalcImage *calcImage = new rsgis::img::RSGISCalcImage(&cloudMaskPass1, "", true);
            datasets = new GDALDataset*[3];
            datasets[0] = reflDataset;
            datasets[1] = thermDataset;
            datasets[2] = saturateDataset;
            GDALDataset *pass1DS = imgUtils.createCopy(reflDataset, 15, pass1TmpOutImage, gdalFormat, GDT_Float32);
            calcImage->calcImage(datasets, 3, pass1DS);
            delete calcImage;
            delete[] datasets;
            
            
            std::cout << "Export Land and Water regions.\n";
            GDALDataset *landWaterClearSkyDS = imgUtils.createCopy(reflDataset, 1, landWaterTmpOutImage, gdalFormat, GDT_UInt32);
            rsgis::calib::RSGISLandsatFMaskExportPass1LandWaterCloudMasking exportLandWaterRegions = rsgis::calib::RSGISLandsatFMaskExportPass1LandWaterCloudMasking();
            calcImage = new rsgis::img::RSGISCalcImage(&exportLandWaterRegions, "", true);
            calcImage->calcImage(&pass1DS, 1, landWaterClearSkyDS);
            delete calcImage;
            
            popImageStats.populateImageWithRasterGISStats(landWaterClearSkyDS, true, true, 1);
            
            std::cout << "Populating RAT with Thermal Stats\n";
            std::vector<rsgis::rastergis::RSGISBandAttPercentiles *> *bandPercentStats = new std::vector<rsgis::rastergis::RSGISBandAttPercentiles *>();
            rsgis::rastergis::RSGISBandAttPercentiles *tempUpperPercent = new rsgis::rastergis::RSGISBandAttPercentiles();
            tempUpperPercent->fieldName = "UpperTempThres";
            tempUpperPercent->percentile = 82.5;
            bandPercentStats->push_back(tempUpperPercent);
            rsgis::rastergis::RSGISBandAttPercentiles *tempLowerPercent = new rsgis::rastergis::RSGISBandAttPercentiles();
            tempLowerPercent->fieldName = "LowerTempThres";
            tempLowerPercent->percentile = 17.5;
            bandPercentStats->push_back(tempLowerPercent);
            calcClumpStats.populateRATWithPercentileStats(landWaterClearSkyDS, thermDataset, 1, bandPercentStats, 1, 200);
            delete tempUpperPercent;
            delete tempLowerPercent;
            delete bandPercentStats;
            
            std::cout << "Get Thresholds From the RAT\n";
            const GDALRasterAttributeTable *landWaterRAT = landWaterClearSkyDS->GetRasterBand(1)->GetDefaultRAT();
            double lowerWaterThres = ratUtils.readDoubleColumnVal(landWaterRAT, "LowerTempThres", 2)/scaleFactorIn;
            double upperWaterThres = ratUtils.readDoubleColumnVal(landWaterRAT, "UpperTempThres", 2)/scaleFactorIn;
            double lowerLandThres = ratUtils.readDoubleColumnVal(landWaterRAT, "LowerTempThres", 1)/scaleFactorIn;
            double upperLandThres = ratUtils.readDoubleColumnVal(landWaterRAT, "UpperTempThres", 1)/scaleFactorIn;
            
            std::cout << "Lower Water Threshold = " << lowerWaterThres << std::endl;
            std::cout << "Upper Water Threshold = " << upperWaterThres << std::endl;
            
            std::cout << "Lower Land Threshold = " << lowerLandThres << std::endl;
            std::cout << "Upper Land Threshold = " << upperLandThres << std::endl;
            
            
            
            std::cout << "Calculate the cloud probability over the land area...\n";
            rsgis::calib::RSGISLandsatFMaskPass2ClearSkyCloudProbCloudMasking cloudMaskPass2Part1 = rsgis::calib::RSGISLandsatFMaskPass2ClearSkyCloudProbCloudMasking(scaleFactorIn, (numReflBands+numThermBands), upperWaterThres, upperLandThres, lowerLandThres);
            calcImage = new rsgis::img::RSGISCalcImage(&cloudMaskPass2Part1, "", true);
            datasets = new GDALDataset*[4];
            datasets[0] = landWaterClearSkyDS;
            datasets[1] = reflDataset;
            datasets[2] = thermDataset;
            datasets[3] = pass1DS;
            GDALDataset *pass2DS = imgUtils.createCopy(reflDataset, 6, cloudLandProbTmpOutImage, gdalFormat, GDT_Float32);
            calcImage->calcImage(datasets, 4, pass2DS);
            delete calcImage;
            delete[] datasets;
            
            std::cout << "Calculate percentile probability thresholds for water and land...\n";
            bandPercentStats = new std::vector<rsgis::rastergis::RSGISBandAttPercentiles *>();
            rsgis::rastergis::RSGISBandAttPercentiles *landCloudProbPercent = new rsgis::rastergis::RSGISBandAttPercentiles();
            landCloudProbPercent->fieldName = "UpperCloudLandThres";
            landCloudProbPercent->percentile = 82.5;
            bandPercentStats->push_back(landCloudProbPercent);
            calcClumpStats.populateRATWithPercentileStats(landWaterClearSkyDS, pass2DS, 6, bandPercentStats, 1, 200);
            delete landCloudProbPercent;
            delete bandPercentStats;
            double landCloudProbUpperThres = ratUtils.readDoubleColumnVal(landWaterRAT, "UpperCloudLandThres", 1);
            
            bandPercentStats = new std::vector<rsgis::rastergis::RSGISBandAttPercentiles *>();
            rsgis::rastergis::RSGISBandAttPercentiles *waterCloudProbPercent = new rsgis::rastergis::RSGISBandAttPercentiles();
            waterCloudProbPercent->fieldName = "UpperCloudWaterThres";
            waterCloudProbPercent->percentile = 82.5;
            bandPercentStats->push_back(waterCloudProbPercent);
            calcClumpStats.populateRATWithPercentileStats(landWaterClearSkyDS, pass2DS, 3, bandPercentStats, 1, 200);
            delete waterCloudProbPercent;
            delete bandPercentStats;
            double waterCloudProbUpperThres = ratUtils.readDoubleColumnVal(landWaterRAT, "UpperCloudWaterThres", 2);
            
            
            landCloudProbUpperThres = landCloudProbUpperThres + 0.2;
            waterCloudProbUpperThres = 0.5;//waterCloudProbUpperThres + 0.2;
            
            std::cout << "Upper Land Cloud Prob Threshold = " << landCloudProbUpperThres << std::endl;
            std::cout << "Upper Water Cloud Prob Threshold = " << waterCloudProbUpperThres << std::endl;
            

            std::cout << "Apply second pass FMask to classify final clouds mask...\n";
            rsgis::calib::RSGISLandsatFMaskPass2CloudMasking cloudMaskPass2Part2 = rsgis::calib::RSGISLandsatFMaskPass2CloudMasking(scaleFactorIn, (numReflBands+numThermBands), landCloudProbUpperThres, waterCloudProbUpperThres);
            calcImage = new rsgis::img::RSGISCalcImage(&cloudMaskPass2Part2, "", true);
            datasets = new GDALDataset*[5];
            datasets[0] = landWaterClearSkyDS;
            datasets[1] = reflDataset;
            datasets[2] = thermDataset;
            datasets[3] = pass1DS;
            datasets[4] = pass2DS;
            GDALDataset *cloudMaskDS = imgUtils.createCopy(reflDataset, 1, outputImage, gdalFormat, GDT_Int32);
            calcImage->calcImage(datasets, 5, cloudMaskDS);
            delete calcImage;
            delete[] datasets;
            
            
            std::cout << "Apply cloud majority filter...\n";
            rsgis::calib::RSGISCalcImageCloudMajorityFilter cloudMajFilter = rsgis::calib::RSGISCalcImageCloudMajorityFilter();
            rsgis::img::RSGISCalcEditImage editImgCalc = rsgis::img::RSGISCalcEditImage(&cloudMajFilter);
            editImgCalc.calcImageWindowData(cloudMaskDS, 5);
            
            std::cout << "Calculate Shadow Mask\n";
            int nirIdx = 4;
            if(reflDataset->GetRasterCount() == 7)
            {
                nirIdx = 5;
            }
            bandPercentStats = new std::vector<rsgis::rastergis::RSGISBandAttPercentiles *>();
            rsgis::rastergis::RSGISBandAttPercentiles *landNIRPercent = new rsgis::rastergis::RSGISBandAttPercentiles();
            landNIRPercent->fieldName = "LowerNIRLandValue175";
            landNIRPercent->percentile = 17.5;
            bandPercentStats->push_back(landNIRPercent);
            calcClumpStats.populateRATWithPercentileStats(landWaterClearSkyDS, reflDataset, nirIdx, bandPercentStats, 1, 200);
            delete landNIRPercent;
            delete bandPercentStats;
            double landNIR175Val = ratUtils.readDoubleColumnVal(landWaterRAT, "LowerNIRLandValue175", 1);
            
            std::cout << "Land NIR 17.5% Percentile = " << landNIR175Val << std::endl;
            
            // Extract NIR band.
            std::cout << "Extract NIR Band\n";
            GDALDataset *nirBandDS = imgUtils.createCopy(reflDataset, 1, tmpNIRBandImg, gdalFormat, imgReflDT);
            std::vector<unsigned int> bands;
            bands.push_back(4);
            rsgis::img::RSGISCopyImageBandSelect selImageBands = rsgis::img::RSGISCopyImageBandSelect(bands);
            rsgis::img::RSGISCalcImage calcSelBandsImage = rsgis::img::RSGISCalcImage(&selImageBands);
            calcSelBandsImage.calcImage(&reflDataset, 1, nirBandDS);
            
            std::cout << "Fill NIR Band\n";
            GDALDataset *nirBandFillDS = imgUtils.createCopy(reflDataset, 1, tmpNIRFillBandImg, gdalFormat, imgReflDT);
            rsgis::calib::RSGISHydroDEMFillSoilleGratin94 fillDEMInst;
            fillDEMInst.performSoilleGratin94Fill(nirBandDS, validAreaDataset, nirBandFillDS, false, landNIR175Val);
     
            //std::string validImg
            //std::string tmpNIRBandImg, std::string tmpNIRFillBandImg, std::string tmpPotentClouds
            std::cout << "Produce Potential Cloud Shadows Mask\n";
            GDALDataset *potentCloudDS = imgUtils.createCopy(reflDataset, 1, tmpPotentClouds, gdalFormat, GDT_Int32);
            rsgis::calib::RSGISCalcImagePotentialCloudShadowsMask imgCalcPotentShadows = rsgis::calib::RSGISCalcImagePotentialCloudShadowsMask(scaleFactorIn);
            rsgis::img::RSGISCalcImage calcPotentShadowImage = rsgis::img::RSGISCalcImage(&imgCalcPotentShadows);
            datasets = new GDALDataset*[3];
            datasets[0] = validAreaDataset;
            datasets[1] = nirBandDS;
            datasets[2] = nirBandFillDS;
            calcPotentShadowImage.calcImage(datasets, 3, potentCloudDS);
            
            popImageStats.populateImageWithRasterGISStats(potentCloudDS, true, true, 1);
            popImageStats.populateImageWithRasterGISStats(cloudMaskDS, true, true, 1);
            
            GDALClose(pass1DS);
            GDALClose(landWaterClearSkyDS);
            GDALClose(pass2DS);
            GDALClose(cloudMaskDS);
            GDALClose(nirBandDS);
            GDALClose(nirBandFillDS);
            GDALClose(potentCloudDS);
            GDALClose(reflDataset);
            GDALClose(thermDataset);
            GDALClose(saturateDataset);
            GDALClose(validAreaDataset);
        }
        catch(RSGISException &e)
        {
            throw RSGISCmdException(e.what());
        }
        catch(std::exception &e)
        {
            throw RSGISCmdException(e.what());
        }
    }
    
                
                
    void executeConvertWorldView2ToRadiance(std::string inputImage, std::string outputImage, std::string gdalFormat, std::vector<CmdsWorldView2RadianceGainsOffsets> wv2RadGainOffs)throw(RSGISCmdException)
    {
        GDALAllRegister();
        
        try
        {
            unsigned int numBands = wv2RadGainOffs.size();
            std::cout << "Opening: " << inputImage << std::endl;
            GDALDataset *inDataset = (GDALDataset *) GDALOpen(inputImage.c_str(), GA_ReadOnly);
            if(inDataset == NULL)
            {
                std::string message = std::string("Could not open image ") + inputImage;
                throw RSGISImageException(message.c_str());
            }
            
            if(inDataset->GetRasterCount() != numBands)
            {
                std::cerr << "Number of input coefficients = " << numBands << std::endl;
                std::cerr << "Number of input image bands = " << inDataset->GetRasterCount() << std::endl;
                throw RSGISImageException("The number of band coefficients needs to equal the number input image bands.");
            }
            
            std::string *outBandNames = new std::string[numBands];
            
            rsgis::calib::WorldView2RadianceGainsOffsets *wv2RadGainOffsInternal = new rsgis::calib::WorldView2RadianceGainsOffsets[numBands];
            
            unsigned int i = 0;
            for(std::vector<rsgis::cmds::CmdsWorldView2RadianceGainsOffsets>::iterator iterBands = wv2RadGainOffs.begin(); iterBands != wv2RadGainOffs.end(); ++iterBands)
            {
                wv2RadGainOffsInternal[i].band = (*iterBands).band;
                wv2RadGainOffsInternal[i].absCalFact = (*iterBands).absCalFact;
                wv2RadGainOffsInternal[i].effBandWidth = (*iterBands).effBandWidth;
                
                outBandNames[i] = (*iterBands).bandName;
                
                //std::cout << "Band " << wv2RadGainOffsInternal[i].band << "(" << outBandNames[i] << "): Abs = " << wv2RadGainOffsInternal[i].absCalFact << " Bandwidth = " << wv2RadGainOffsInternal[i].effBandWidth << std::endl;
                
                ++i;
            }
            
            rsgis::calib::RSGISWorldView2RadianceCalibration *radianceCalibration = new rsgis::calib::RSGISWorldView2RadianceCalibration(numBands, wv2RadGainOffsInternal);
            rsgis::img::RSGISCalcImage *calcImage = new rsgis::img::RSGISCalcImage(radianceCalibration, "", true);
            
            calcImage->calcImage(&inDataset, 1, outputImage, true, outBandNames, gdalFormat);

            GDALClose(inDataset);
            delete[] wv2RadGainOffsInternal;
            delete[] outBandNames;
            
            delete radianceCalibration;
            delete calcImage;
        }
        catch(RSGISException &e)
        {
            throw RSGISCmdException(e.what());
        }
        catch(std::exception &e)
        {
            throw RSGISCmdException(e.what());
        }
    }

                
    void executeConvertSPOT5ToRadiance(std::string inputImage, std::string outputImage, std::string gdalFormat, std::vector<CmdsSPOTRadianceGainsOffsets> spot5RadGainOffs)throw(RSGISCmdException)
    {
        GDALAllRegister();
        
        try
        {
            unsigned int numBands = spot5RadGainOffs.size();
            std::cout << "Opening: " << inputImage << std::endl;
            GDALDataset *inDataset = (GDALDataset *) GDALOpen(inputImage.c_str(), GA_ReadOnly);
            if(inDataset == NULL)
            {
                std::string message = std::string("Could not open image ") + inputImage;
                throw RSGISImageException(message.c_str());
            }
            
            if(inDataset->GetRasterCount() != numBands)
            {
                std::cerr << "Number of input coefficients = " << numBands << std::endl;
                std::cerr << "Number of input image bands = " << inDataset->GetRasterCount() << std::endl;
                throw RSGISImageException("The number of band coefficients needs to equal the number input image bands.");
            }
            
            std::string *outBandNames = new std::string[numBands];
            
            rsgis::calib::SPOTRadianceGainsOffsets *spot5RadGainOffsInternal = new rsgis::calib::SPOTRadianceGainsOffsets[numBands];
            
            unsigned int i = 0;
            for(std::vector<rsgis::cmds::CmdsSPOTRadianceGainsOffsets>::iterator iterBands = spot5RadGainOffs.begin(); iterBands != spot5RadGainOffs.end(); ++iterBands)
            {
                if(((*iterBands).band < 1) | ((*iterBands).band > 4))
                {
                    throw RSGISImageException("Image bands must be between 1 and 4.");
                }
                
                spot5RadGainOffsInternal[i].band = (*iterBands).band;
                spot5RadGainOffsInternal[i].gain = (*iterBands).gain;
                spot5RadGainOffsInternal[i].bias = (*iterBands).bias;
                
                outBandNames[spot5RadGainOffsInternal[i].band-1] = (*iterBands).bandName;
                ++i;
            }
            
            rsgis::calib::RSGISSPOTRadianceCalibration *radianceCalibration = new rsgis::calib::RSGISSPOTRadianceCalibration(numBands, spot5RadGainOffsInternal);
            rsgis::img::RSGISCalcImage *calcImage = new rsgis::img::RSGISCalcImage(radianceCalibration, "", true);
            
            calcImage->calcImage(&inDataset, 1, outputImage, true, outBandNames, gdalFormat);
            
            GDALClose(inDataset);
            delete[] spot5RadGainOffsInternal;
            delete[] outBandNames;
            
            delete radianceCalibration;
            delete calcImage;
        }
        catch(RSGISException &e)
        {
            throw RSGISCmdException(e.what());
        }
        catch(std::exception &e)
        {
            throw RSGISCmdException(e.what());
        }
    }
                
    void executeApplySubtractSingleOffsets(std::string inputImage, std::string outputImage, std::vector<double> offsetValues, bool nonNegative, std::string gdalFormat, rsgis::RSGISLibDataType rsgisOutDataType, float noDataVal, bool useNoDataVal, float darkObjReflVal) throw(RSGISCmdException)
    {
        try
        {
            GDALAllRegister();
            
            std::cout << "Open input image: \'" << inputImage << "\'" << std::endl;
            GDALDataset *dataset = (GDALDataset *) GDALOpen(inputImage.c_str(), GA_ReadOnly);
            if(dataset == NULL)
            {
                std::string message = std::string("Could not open image ") + inputImage;
                throw rsgis::RSGISImageException(message.c_str());
            }

            
            if(dataset->GetRasterCount() != offsetValues.size())
            {
                throw rsgis::RSGISImageException("The two input images need to have the same number of image bands.");
            }
            int numRasterBands = dataset->GetRasterCount();
            
            std::cout << "Apply offsets to input image...\n";
            rsgis::calib::RSGISApplyDarkObjSubtractSingleOffsets *applyOffsets = new rsgis::calib::RSGISApplyDarkObjSubtractSingleOffsets(numRasterBands, offsetValues, nonNegative, noDataVal, useNoDataVal, darkObjReflVal);
            
            rsgis::img::RSGISCalcImage *calcImage = new rsgis::img::RSGISCalcImage(applyOffsets, "", true);
            calcImage->calcImage(&dataset, 1, outputImage, false, NULL, gdalFormat, RSGIS_to_GDAL_Type(rsgisOutDataType));
            
            delete applyOffsets;
            delete calcImage;
            
            GDALClose(dataset);
        }
        catch(rsgis::RSGISException &e)
        {
            throw RSGISCmdException(e.what());
        }
        catch(std::exception &e)
        {
            throw RSGISCmdException(e.what());
        }
    }
                
    
}}



