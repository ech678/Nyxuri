qt_add_library(ClavisNiri SHARED)

set_target_properties(ClavisNiri PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CLAVIS_QML_BUILD_DIR}/Clavis/Niri
)

qt_add_qml_module(ClavisNiri
    URI Clavis.Niri
    SOURCES
        src/niri_plugin.h
        src/niri_plugin.cpp
        src/niri_floating_parallax.h
        src/niri_floating_parallax.cpp
        src/niri_animation_targets.h
        src/niri_animation_targets.cpp
    OUTPUT_DIRECTORY ${CLAVIS_QML_BUILD_DIR}/Clavis/Niri
)

target_include_directories(ClavisNiri PUBLIC src)

target_link_libraries(ClavisNiri PRIVATE
    ClavisNiriCore
    Qt6::Core
    Qt6::Gui
    Qt6::Qml
    Qt6::Network
)
