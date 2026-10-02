#pragma once

#include <QProcessEnvironment>
#include <QString>

namespace Clavis::Runtime {

class ClavisPaths {
  public:
    static ClavisPaths fromEnvironment();

    QString home() const;
    QString binHome() const;
    QString configHome() const;
    QString dataHome() const;
    QString stateHome() const;
    QString cacheHome() const;
    QString runtimeHome() const;
    QString profileName() const;
    QString profileConfigHome() const;
    QString profileHome() const;
    QString generatedHome() const;
    QString stableKey() const;

  private:
    static QString cleanAbsolute(const QString &value);
    static QString environmentPath(const char *overrideName, const char *xdgName, const QString &fallback,
                                   const QString &suffix);

    QString m_home;
    QString m_binHome;
    QString m_stableKey;
    QString m_configHome;
    QString m_dataHome;
    QString m_stateHome;
    QString m_cacheHome;
    QString m_runtimeHome;
    QString m_profileName;
    QString m_profileConfigHome;
    QString m_profileHome;
    QString m_generatedHome;
};

} // namespace Clavis::Runtime
