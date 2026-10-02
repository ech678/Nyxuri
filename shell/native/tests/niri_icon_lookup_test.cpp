#include "niri_icon_lookup.h"

#include <QDir>
#include <QFile>
#include <QTemporaryDir>
#include <QTest>
#include <QUrl>

class NiriIconLookupTest : public QObject {
    Q_OBJECT

  private slots:
    void resolvesDesktopIcon_data()
    {
        QTest::addColumn<QString>("iconName");
        QTest::addColumn<QString>("fileName");
        QTest::newRow("reverse-dns-svg") << "app.zen_browser.zen" << "app.zen_browser.zen.svg";
        QTest::newRow("reverse-dns-png") << "app.zen_browser.zen" << "app.zen_browser.zen.png";
        QTest::newRow("reverse-dns-xpm") << "app.zen_browser.zen" << "app.zen_browser.zen.xpm";
        QTest::newRow("plain-name") << "clavis-test-browser" << "clavis-test-browser.svg";
        QTest::newRow("explicit-extension") << "app.zen_browser.zen.svg" << "app.zen_browser.zen.svg";
    }

    void resolvesDesktopIcon()
    {
        QFETCH(QString, iconName);
        QFETCH(QString, fileName);
        QTemporaryDir directory;
        QVERIFY(directory.isValid());
        // Isolate discovery from installed applications and icon themes.
        const auto oldHome = qgetenv("XDG_DATA_HOME");
        const auto oldDirs = qgetenv("XDG_DATA_DIRS");
        const auto restore = qScopeGuard([&] {
            oldHome.isNull() ? qunsetenv("XDG_DATA_HOME") : qputenv("XDG_DATA_HOME", oldHome);
            oldDirs.isNull() ? qunsetenv("XDG_DATA_DIRS") : qputenv("XDG_DATA_DIRS", oldDirs);
        });
        qputenv("XDG_DATA_HOME", directory.path().toUtf8());
        qputenv("XDG_DATA_DIRS", directory.path().toUtf8());
        QVERIFY(QDir().mkpath(directory.path() + "/applications"));
        QVERIFY(QDir().mkpath(directory.path() + "/icons/hicolor/scalable/apps"));
        QFile desktop(directory.path() + "/applications/app.zen_browser.zen.desktop");
        QVERIFY(desktop.open(QIODevice::WriteOnly));
        desktop.write("[Desktop Entry]\nType=Application\nName=Fixture Browser\nIcon=" + iconName.toUtf8() +
                      "\n");
        desktop.close();
        const QString path = directory.path() + "/icons/hicolor/scalable/apps/" + fileName;
        QFile icon(path);
        QVERIFY(icon.open(QIODevice::WriteOnly));
        icon.close();

        NiriIconLookup lookup;
        const auto result = lookup.resolve("app.zen_browser.zen");
        QCOMPARE(result.appName, QStringLiteral("Fixture Browser"));
        QCOMPARE(result.iconPath, QUrl::fromLocalFile(path).toString());
    }
};

QTEST_GUILESS_MAIN(NiriIconLookupTest)
#include "niri_icon_lookup_test.moc"
