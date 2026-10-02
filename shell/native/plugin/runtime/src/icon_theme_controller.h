#pragma once

#include <QObject>
#include <QtQml/qqmlregistration.h>

class IconThemeController : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
    Q_PROPERTY(QString systemThemeName READ systemThemeName CONSTANT)
    Q_PROPERTY(QString themeName READ themeName NOTIFY changed)
    Q_PROPERTY(int revision READ revision NOTIFY changed)

  public:
    explicit IconThemeController(QObject *parent = nullptr);
    QString systemThemeName() const;
    QString themeName() const;
    int revision() const { return m_revision; }
    Q_INVOKABLE void setThemeName(const QString &name);

  signals:
    void changed();

  private:
    int m_revision = 0;
};
