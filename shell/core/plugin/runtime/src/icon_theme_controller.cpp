#include "icon_theme_controller.h"

#include <QIcon>

namespace {
QString startupThemeName()
{
    // Keep the platform default across QML engine reloads in the same process.
    static const QString name = QIcon::themeName();
    return name;
}
} // namespace

IconThemeController::IconThemeController(QObject *parent) : QObject(parent) { startupThemeName(); }

QString IconThemeController::systemThemeName() const { return startupThemeName(); }

QString IconThemeController::themeName() const { return QIcon::themeName(); }

void IconThemeController::setThemeName(const QString &name)
{
    const auto effective = name.isEmpty() ? systemThemeName() : name;
    if (QIcon::themeName() == effective)
        return;
    QIcon::setThemeName(effective);
    ++m_revision;
    emit changed();
}
