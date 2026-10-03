qt_add_library(ClavisI18n SHARED)
add_dependencies(ClavisI18n search_catalog)

set_target_properties(ClavisI18n PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CLAVIS_QML_BUILD_DIR}/Clavis/I18n
)

qt_add_qml_module(ClavisI18n
    URI Clavis.I18n
    SOURCES
        src/i18n_manager.h
        src/i18n_manager.cpp
    OUTPUT_DIRECTORY ${CLAVIS_QML_BUILD_DIR}/Clavis/I18n
)

file(GLOB_RECURSE CLAVIS_TRANSLATION_SOURCES CONFIGURE_DEPENDS
    "${CLAVIS_SOURCE_ROOT}/app/*.js"
    "${CLAVIS_SOURCE_ROOT}/app/*.qml"
    "${CLAVIS_SOURCE_ROOT}/modules/*.js"
    "${CLAVIS_SOURCE_ROOT}/modules/*.qml"
    "${CLAVIS_SOURCE_ROOT}/shared/*.js"
    "${CLAVIS_SOURCE_ROOT}/shared/*.qml"
)
list(APPEND CLAVIS_TRANSLATION_SOURCES
    "${CLAVIS_SOURCE_ROOT}/native/plugin/keyboard/src/shortcut_recorder.cpp"
    "${CLAVIS_SOURCE_ROOT}/shell.qml"
    "${CLAVIS_SOURCE_ROOT}/native/tools/window-preview/Preview.qml"
)

set(GENERATED_QM_EN "${CMAKE_CURRENT_BINARY_DIR}/clavis_en_US.qm")
set(GENERATED_QM_ZH "${CMAKE_CURRENT_BINARY_DIR}/clavis_zh_CN.qm")

add_custom_command(
    OUTPUT "${GENERATED_QM_EN}" "${GENERATED_QM_ZH}"
    COMMAND "${Python3_EXECUTABLE}" "${CLAVIS_SOURCE_ROOT}/scripts/dev/compile-i18n.py"
        --input-dir "${CLAVIS_SOURCE_ROOT}/assets/i18n"
        --output-dir "${CMAKE_CURRENT_BINARY_DIR}"
        --source-root "${CLAVIS_SOURCE_ROOT}"
        --prefix "clavis"
        --compile-qm
    DEPENDS
        "${CLAVIS_SOURCE_ROOT}/assets/i18n/zh_CN.toml"
        "${CLAVIS_SOURCE_ROOT}/assets/i18n/en_US.toml"
        "${CLAVIS_SOURCE_ROOT}/scripts/dev/compile-i18n.py"
    VERBATIM
)

set_source_files_properties("${GENERATED_QM_EN}" PROPERTIES QT_RESOURCE_ALIAS "clavis_en_US.qm")
set_source_files_properties("${GENERATED_QM_ZH}" PROPERTIES QT_RESOURCE_ALIAS "clavis_zh_CN.qm")

qt_add_resources(ClavisI18n "translations"
    PREFIX "/i18n"
    FILES
        "${GENERATED_QM_EN}"
        "${GENERATED_QM_ZH}"
)

target_include_directories(ClavisI18n PUBLIC src)

target_link_libraries(ClavisI18n PRIVATE
    Qt6::Core
    Qt6::Qml
)
