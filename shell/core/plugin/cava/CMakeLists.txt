qt_add_library(ClavisCava SHARED)

set_target_properties(ClavisCava PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CLAVIS_QML_BUILD_DIR}/Clavis/Cava
)

qt_add_qml_module(ClavisCava
    URI Clavis.Cava
    SOURCES
        src/cava_provider.h
        src/cava_provider.cpp
        src/audio_level_provider.h
        src/audio_level_provider.cpp
    OUTPUT_DIRECTORY ${CLAVIS_QML_BUILD_DIR}/Clavis/Cava
)

target_include_directories(ClavisCava PUBLIC src)

target_link_libraries(ClavisCava PRIVATE
    ClavisCavaCore
    Qt6::Core
    Qt6::Gui
    Qt6::Qml
    PkgConfig::Cava
)
