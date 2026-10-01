#include "icon_theme_controller.h"

#include <QDir>
#include <QFile>
#include <QIcon>
#include <QImage>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QTest>

class IconThemeControllerTest : public QObject {
    Q_OBJECT

  private slots:
    void switchesRenderedIconsAndRestoresStartupDefault();
};

void IconThemeControllerTest::switchesRenderedIconsAndRestoresStartupDefault()
{
    QTemporaryDir directory;
    QVERIFY(directory.isValid());
    const auto writeTheme = [&](const QString &name, const QString &inherits, const QColor &color) {
        const QString base = directory.path() + '/' + name;
        if (!QDir().mkpath(base + "/32x32/apps"))
            return false;
        QFile index(base + "/index.theme");
        if (!index.open(QIODevice::WriteOnly))
            return false;
        const QByteArray contents = QString("[Icon Theme]\nName=%1\nInherits=%2\n"
                                            "Directories=32x32/apps\n[32x32/apps]\n"
                                            "Size=32\nType=Fixed\nContext=Applications\n")
                                        .arg(name, inherits)
                                        .toUtf8();
        if (index.write(contents) != contents.size())
            return false;
        index.close();
        QImage image(32, 32, QImage::Format_ARGB32);
        image.fill(color);
        return image.save(base + "/32x32/apps/clavis-test-app.png");
    };
    QVERIFY(writeTheme("ClavisTestDefault", "hicolor", Qt::red));
    QVERIFY(writeTheme("ClavisTestSelected", "ClavisTestDefault", Qt::blue));
    QImage inherited(32, 32, QImage::Format_ARGB32);
    inherited.fill(Qt::green);
    QVERIFY(inherited.save(directory.path() + "/ClavisTestDefault/32x32/apps/clavis-test-inherited.png"));

    QIcon::setThemeSearchPaths({directory.path()});
    QIcon::setThemeName("ClavisTestDefault");
    IconThemeController controller;
    QSignalSpy changed(&controller, &IconThemeController::changed);
    const auto pixel = [](const QString &name) {
        return QIcon::fromTheme(name).pixmap(32, 32).toImage().pixelColor(16, 16);
    };
    QCOMPARE(controller.systemThemeName(), QString("ClavisTestDefault"));
    QCOMPARE(pixel("clavis-test-app"), QColor(Qt::red));
    controller.setThemeName("ClavisTestSelected");
    QCOMPARE(controller.themeName(), QString("ClavisTestSelected"));
    QCOMPARE(controller.revision(), 1);
    QCOMPARE(changed.count(), 1);
    QCOMPARE(pixel("clavis-test-app"), QColor(Qt::blue));
    QCOMPARE(pixel("clavis-test-inherited"), QColor(Qt::green));
    controller.setThemeName("ClavisTestSelected");
    QCOMPARE(changed.count(), 1);

    // A replacement QML singleton must not capture the user's override as default.
    IconThemeController reloaded;
    QCOMPARE(reloaded.systemThemeName(), QString("ClavisTestDefault"));
    controller.setThemeName("");
    QCOMPARE(controller.themeName(), QString("ClavisTestDefault"));
    QCOMPARE(controller.revision(), 2);
    QCOMPARE(changed.count(), 2);
    QCOMPARE(pixel("clavis-test-app"), QColor(Qt::red));
}

QTEST_MAIN(IconThemeControllerTest)
#include "icon_theme_controller_test.moc"
