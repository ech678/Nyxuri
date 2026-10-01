pkg_check_modules(WaylandClient REQUIRED IMPORTED_TARGET wayland-client)
pkg_check_modules(WaylandProtocols REQUIRED wayland-protocols>=1.41)
pkg_get_variable(WAYLAND_PROTOCOLS_DIR wayland-protocols pkgdatadir)
find_program(WAYLAND_SCANNER wayland-scanner REQUIRED)
set(capture_protocols)
foreach(protocol ext-foreign-toplevel-list ext-image-capture-source ext-image-copy-capture)
    set(xml "${WAYLAND_PROTOCOLS_DIR}/staging/${protocol}/${protocol}-v1.xml")
    set(header "${CMAKE_CURRENT_BINARY_DIR}/${protocol}-v1-client-protocol.h")
    set(code "${CMAKE_CURRENT_BINARY_DIR}/${protocol}-v1-protocol.c")
    add_custom_command(OUTPUT "${header}" "${code}"
        COMMAND ${WAYLAND_SCANNER} client-header "${xml}" "${header}"
        COMMAND ${WAYLAND_SCANNER} private-code "${xml}" "${code}"
        DEPENDS "${xml}" VERBATIM)
    list(APPEND capture_protocols "${header}" "${code}")
endforeach()
qt_add_library(ClavisWindowPreview SHARED)
set_target_properties(ClavisWindowPreview PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CLAVIS_QML_BUILD_DIR}/Clavis/WindowPreview)
qt_add_qml_module(ClavisWindowPreview
    URI Clavis.WindowPreview
    SOURCES src/window_capture_probe.h src/window_capture_probe.cpp
        src/window_preview_manager.h src/window_preview_manager.cpp
        src/window_preview_cache.h src/window_preview_cache.cpp
        src/capture_image.h src/capture_image.cpp ${capture_protocols}
    OUTPUT_DIRECTORY ${CLAVIS_QML_BUILD_DIR}/Clavis/WindowPreview)
target_include_directories(ClavisWindowPreview PUBLIC src PRIVATE ${CMAKE_CURRENT_BINARY_DIR})
target_link_libraries(ClavisWindowPreview PRIVATE Qt6::Quick Qt6::Qml PkgConfig::WaylandClient)
option(CLAVIS_BUILD_WINDOW_PREVIEW_PROBE "Build the standalone ext window capture probe" OFF)
if(CLAVIS_BUILD_WINDOW_PREVIEW_PROBE)
    add_subdirectory(${CLAVIS_SOURCE_ROOT}/tools/window-preview ${CMAKE_CURRENT_BINARY_DIR}/probe)
endif()
