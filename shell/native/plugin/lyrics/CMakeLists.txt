qt_add_library(ClavisLyrics SHARED)

set_target_properties(ClavisLyrics PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CLAVIS_QML_BUILD_DIR}/Clavis/Lyrics
)

qt_add_qml_module(ClavisLyrics
    URI Clavis.Lyrics
    SOURCES
        src/lyrics.h
        src/lyrics.cpp
    OUTPUT_DIRECTORY ${CLAVIS_QML_BUILD_DIR}/Clavis/Lyrics
)

target_include_directories(ClavisLyrics PUBLIC src)

target_link_libraries(ClavisLyrics PRIVATE
    Qt6::Core
    Qt6::Network
    Qt6::Qml
)
