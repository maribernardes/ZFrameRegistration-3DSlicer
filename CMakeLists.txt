cmake_minimum_required(VERSION 3.5)

project(ZFrameCalibration)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "http://slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/ZFrameCalibration")
set(EXTENSION_CATEGORY "IGT")
set(EXTENSION_CONTRIBUTORS " Christian Herz (SPL), Longquan Chen (SPL), Junichi Tokuda (SPL), Andrey Fedorov (SPL)")
set(EXTENSION_DESCRIPTION "This extension provides support for procedures with ZFrame Calibration")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/ZFrameCalibration.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/ZFrameCalibration/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a space separated string, a list or 'NA' if any

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(ZFrameCalibration)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
