cmake_minimum_required(VERSION 3.5)

project(ZFrameCalibration)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "http://slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/ZFrameCalibration")
set(EXTENSION_CATEGORY "IGT")
set(EXTENSION_CONTRIBUTORS "Junichi Tokuda (SPL), Longquan Chen (SPL), Christian Herz (SPL), Andrey Fedorov (SPL)")
set(EXTENSION_DESCRIPTION "This extension provides support for procedures with ZFrame Calibration")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/ZFrameCalibration.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/ZFrameCalibration/Screenshots/1.png")

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
