cmake_minimum_required(VERSION 3.21)

file(STRINGS "${CMAKE_CURRENT_SOURCE_DIR}/VERSION" PROJECT_DATE_VERSION LIMIT_COUNT 1)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/VERSION")
project(ClavisShell VERSION ${PROJECT_DATE_VERSION} LANGUAGES C CXX)

include(GNUInstallDirs)
include(CTest)

set(CLAVIS_QML_BUILD_DIR "${CMAKE_BINARY_DIR}/qml" CACHE PATH
    "Build-tree QML import root")
set(CLAVIS_QML_INSTALL_DIR "${CMAKE_INSTALL_LIBDIR}/qt6/qml" CACHE PATH
    "Install destination for Clavis private QML modules")
set(CLAVIS_CONFIG_INSTALL_DIR "etc/xdg/quickshell/clavis" CACHE PATH
    "Install destination for the Quickshell clavis configuration")
set(CLAVIS_SYSTEMD_USER_INSTALL_DIR "${CMAKE_INSTALL_LIBDIR}/systemd/user" CACHE PATH
    "Install destination for Clavis systemd user units")

find_package(Python3 REQUIRED COMPONENTS Interpreter)
file(GLOB SEARCH_DECLARATIONS CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/Modules/ControlCenter/*.qml")
set(SEARCH_CATALOG "${CMAKE_CURRENT_SOURCE_DIR}/Common/generated/SearchCatalog.js")
add_custom_command(OUTPUT "${SEARCH_CATALOG}"
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/scripts/dev/generate-search-catalog.py"
    DEPENDS ${SEARCH_DECLARATIONS}
        "${CMAKE_CURRENT_SOURCE_DIR}/Common/settings-routes.json"
        "${CMAKE_CURRENT_SOURCE_DIR}/scripts/system/niri-actions.json"
        "${CMAKE_CURRENT_SOURCE_DIR}/scripts/dev/generate-search-catalog.py"
    VERBATIM)
add_custom_target(search_catalog ALL DEPENDS "${SEARCH_CATALOG}")

add_subdirectory(core)
