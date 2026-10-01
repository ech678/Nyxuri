#include "clavis_paths.h"

#include <QDir>

namespace Clavis::Runtime {
namespace {

QString env(const char *name) { return QString::fromLocal8Bit(qgetenv(name)).trimmed(); }

} // namespace

ClavisPaths ClavisPaths::fromEnvironment()
{
    ClavisPaths paths;
    paths.m_home = cleanAbsolute(env("HOME"));
    if (paths.m_home.isEmpty())
        paths.m_home = cleanAbsolute(QDir::homePath());

    paths.m_binHome = cleanAbsolute(env("CLAVIS_BIN_HOME"));
    if (paths.m_binHome.isEmpty())
        paths.m_binHome = paths.m_home + QStringLiteral("/.local/bin");

    paths.m_stableKey = cleanAbsolute(env("CLAVIS_KEY"));
    if (paths.m_stableKey.isEmpty())
        paths.m_stableKey = QStringLiteral("key");

    paths.m_configHome = environmentPath("CLAVIS_CONFIG_HOME", "XDG_CONFIG_HOME",
                                         paths.m_home + QStringLiteral("/.config"), QStringLiteral("clavis"));
    paths.m_dataHome =
        environmentPath("CLAVIS_DATA_HOME", "XDG_DATA_HOME", paths.m_home + QStringLiteral("/.local/share"),
                        QStringLiteral("clavis"));
    paths.m_stateHome =
        environmentPath("CLAVIS_STATE_HOME", "XDG_STATE_HOME", paths.m_home + QStringLiteral("/.local/state"),
                        QStringLiteral("clavis"));
    paths.m_cacheHome = environmentPath("CLAVIS_CACHE_HOME", "XDG_CACHE_HOME",
                                        paths.m_home + QStringLiteral("/.cache"), QStringLiteral("clavis"));

    paths.m_runtimeHome = cleanAbsolute(env("CLAVIS_RUNTIME_HOME"));
    if (paths.m_runtimeHome.isEmpty()) {
        QString runtimeBase = cleanAbsolute(env("XDG_RUNTIME_DIR"));
        if (runtimeBase.isEmpty())
            runtimeBase = paths.m_cacheHome + QStringLiteral("/runtime");
        paths.m_runtimeHome = QDir(runtimeBase).filePath(QStringLiteral("clavis"));
    }

    paths.m_profileName = env("CLAVIS_PROFILE");
    if (paths.m_profileName.isEmpty() || paths.m_profileName.contains(QLatin1Char('/')) ||
        paths.m_profileName.contains(QLatin1Char('\\')) || paths.m_profileName == QStringLiteral(".") ||
        paths.m_profileName == QStringLiteral("..")) {
        paths.m_profileName = QStringLiteral("default");
    }
    paths.m_profileHome = cleanAbsolute(env("CLAVIS_PROFILE_HOME"));
    if (paths.m_profileHome.isEmpty()) {
        paths.m_profileHome =
            QDir(paths.m_dataHome).filePath(QStringLiteral("profiles/%1").arg(paths.m_profileName));
    }
    paths.m_profileConfigHome = cleanAbsolute(env("CLAVIS_PROFILE_CONFIG_HOME"));
    if (paths.m_profileConfigHome.isEmpty()) {
        paths.m_profileConfigHome =
            QDir(paths.m_configHome).filePath(QStringLiteral("profiles/%1").arg(paths.m_profileName));
    }
    paths.m_generatedHome = cleanAbsolute(env("CLAVIS_GENERATED_HOME"));
    if (paths.m_generatedHome.isEmpty()) {
        paths.m_generatedHome = QDir(paths.m_profileHome).filePath(QStringLiteral("generated"));
    }
    return paths;
}

QString ClavisPaths::home() const { return m_home; }
QString ClavisPaths::binHome() const { return m_binHome; }
QString ClavisPaths::configHome() const { return m_configHome; }
QString ClavisPaths::dataHome() const { return m_dataHome; }
QString ClavisPaths::stateHome() const { return m_stateHome; }
QString ClavisPaths::cacheHome() const { return m_cacheHome; }
QString ClavisPaths::runtimeHome() const { return m_runtimeHome; }
QString ClavisPaths::profileName() const { return m_profileName; }
QString ClavisPaths::profileConfigHome() const { return m_profileConfigHome; }
QString ClavisPaths::profileHome() const { return m_profileHome; }
QString ClavisPaths::generatedHome() const { return m_generatedHome; }
QString ClavisPaths::stableKey() const { return m_stableKey; }

QString ClavisPaths::cleanAbsolute(const QString &value)
{
    if (value.isEmpty() || !QDir::isAbsolutePath(value))
        return {};
    return QDir::cleanPath(value);
}

QString ClavisPaths::environmentPath(const char *overrideName, const char *xdgName, const QString &fallback,
                                     const QString &suffix)
{
    const QString overridePath = cleanAbsolute(env(overrideName));
    if (!overridePath.isEmpty())
        return overridePath;
    QString base = cleanAbsolute(env(xdgName));
    if (base.isEmpty())
        base = cleanAbsolute(fallback);
    return QDir(base).filePath(suffix);
}

} // namespace Clavis::Runtime
