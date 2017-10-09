cmake_minimum_required(VERSION 3.5)

project(ZFrameRegistration)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "http://slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/ZFrameRegistration")
set(EXTENSION_CATEGORY "IGT")
set(EXTENSION_CONTRIBUTORS "Junichi Tokuda (SPL), Longquan Chen (SPL), Christian Herz (SPL), Andrey Fedorov (SPL)")
set(EXTENSION_DESCRIPTION "This extension provides support for procedures with ZFrame Registration")
set(EXTENSION_ICONURL "https://github.com/leochan2009/SlicerZFrameRegistration/tree/master/ZFrameRegistration/Resources/Icons/ZFrameRegistration.png")
set(EXTENSION_SCREENSHOTURLS "https://github.com/leochan2009/SlicerZFrameRegistration/tree/master/Screenshots/1.png https://github.com/leochan2009/SlicerZFrameRegistration/tree/master/Screenshots/2.png")

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(ZFrameRegistration)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
