/*
 *  RSGISCalcClusterLocation.h
 *  RSGIS_LIB
 *
 *  Created by Pete Bunting on 28/07/2012.
 *  Copyright 2012 RSGISLib.
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

#ifndef RSGISCalcClusterLocation_H
#define RSGISCalcClusterLocation_H

#include <iostream>
#include <string>
#include <cmath>

#include "gdal_priv.h"
#include "gdal_rat.h"

#include "common/RSGISAttributeTableException.h"

#include "rastergis/RSGISRasterAttUtils.h"

#include "img/RSGISImageCalcException.h"
#include "img/RSGISCalcImageValue.h"
#include "img/RSGISCalcImage.h"

#include <boost/numeric/conversion/cast.hpp>
#include <boost/lexical_cast.hpp>

// mark all exported classes/functions with DllExport to have
// them exported by Visual Studio
#undef DllExport
#ifdef _MSC_VER
    #ifdef rsgis_rastergis_EXPORTS
        #define DllExport   __declspec( dllexport )
    #else
        #define DllExport   __declspec( dllimport )
    #endif
#else
    #define DllExport
#endif

namespace rsgis{namespace rastergis{
	
    class DllExport RSGISCalcClusterLocation
    {
    public:
        RSGISCalcClusterLocation();
        void populateAttWithClumpLocation(GDALDataset *dataset, unsigned int ratBand, std::string eastColumn, std::string northColumn);
        void populateAttWithClumpLocationExtent(GDALDataset *dataset, unsigned int ratBand, std::string minXColX, std::string minXColY, std::string maxXColX, std::string maxXColY, std::string minYColX, std::string minYColY, std::string maxYColX, std::string maxYColY);
        void populateAttWithClumpPxlLocation(GDALDataset *dataset, unsigned int ratBand, std::string minXCol, std::string maxXCol, std::string minYCol, std::string maxYCol);
        ~RSGISCalcClusterLocation();
    };
    
    
    
	class DllExport RSGISCalcClusterLocationCalcValue : public rsgis::img::RSGISCalcImageValue
	{
	public: 
		RSGISCalcClusterLocationCalcValue(double **spatialLoc, unsigned int ratBand);
		void calcImageValue(long *intBandValues, unsigned int numIntVals, float *floatBandValues, unsigned int numfloatVals, OGREnvelope extent);
		~RSGISCalcClusterLocationCalcValue();
    private:
        double **spatialLoc;
        unsigned int ratBand;
	};
    
    class DllExport RSGISCalcClusterExtentCalcValue : public rsgis::img::RSGISCalcImageValue
    {
    public:
        RSGISCalcClusterExtentCalcValue(double **spatialLoc, bool *first, unsigned int ratBand);
        void calcImageValue(long *intBandValues, unsigned int numIntVals, float *floatBandValues, unsigned int numfloatVals, OGREnvelope extent);
        ~RSGISCalcClusterExtentCalcValue();
    private:
        double **spatialLoc;
        bool *first;
        unsigned int ratBand;
    };
    
    class DllExport RSGISCalcClusterPxlExtentCalcValue : public rsgis::img::RSGISCalcImageValue
    {
    public:
        RSGISCalcClusterPxlExtentCalcValue(unsigned long **pxlLoc, bool *first, unsigned int ratBand);
        void calcImageValue(long *intBandValues, unsigned int numIntVals, float *floatBandValues, unsigned int numfloatVals, OGREnvelope extent);
        ~RSGISCalcClusterPxlExtentCalcValue();
    private:
        unsigned long **pxlLoc;
        bool *first;
        unsigned int ratBand;
    };
	
}}

#endif

