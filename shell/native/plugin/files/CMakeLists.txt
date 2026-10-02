find_package(Qt6 REQUIRED COMPONENTS Concurrent)
pkg_check_modules(Gio REQUIRED IMPORTED_TARGET gio-unix-2.0)
qt_add_library(ClavisFiles SHARED)
set_target_properties(ClavisFiles PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${CLAVIS_QML_BUILD_DIR}/Clavis/Files)
qt_add_qml_module(ClavisFiles
    URI Clavis.Files
    SOURCES src/file_metadata.h src/file_metadata.cpp
            src/folder_sort_model.h src/folder_sort_model.cpp
            src/desktop_files.h src/desktop_files.cpp
    OUTPUT_DIRECTORY ${CLAVIS_QML_BUILD_DIR}/Clavis/Files
)
target_link_libraries(ClavisFiles PRIVATE Qt6::Core Qt6::Gui Qt6::Qml Qt6::Concurrent PkgConfig::Gio)

target_include_directories(ClavisFiles PRIVATE src)
