qt_add_library(ClavisDesktopCardsCore STATIC)

target_sources(ClavisDesktopCardsCore PRIVATE
    src/wallpaper_analyzer.h
    src/wallpaper_analyzer.cpp
)

set_target_properties(ClavisDesktopCardsCore PROPERTIES
    POSITION_INDEPENDENT_CODE ON
)

target_link_libraries(ClavisDesktopCardsCore PUBLIC
    Qt6::Core
    Qt6::Gui
    Qt6::Qml
)

target_include_directories(ClavisDesktopCardsCore PUBLIC src)

qt_add_library(ClavisDesktopCards SHARED)

set_target_properties(ClavisDesktopCards PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CLAVIS_QML_BUILD_DIR}/Clavis/DesktopCards
)

qt_add_qml_module(ClavisDesktopCards
    URI Clavis.DesktopCards
    SOURCES
        src/wallpaper_analyzer.h
        src/wallpaper_analyzer.cpp
    OUTPUT_DIRECTORY ${CLAVIS_QML_BUILD_DIR}/Clavis/DesktopCards
)

target_include_directories(ClavisDesktopCards PUBLIC src)

target_link_libraries(ClavisDesktopCards PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Qml
)
