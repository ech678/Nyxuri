#include "runtime/clavis_paths.h"

#include <QDir>
#include <QFile>
#include <QTemporaryDir>
#include <QTest>

class ClavisPathsTest : public QObject {
    Q_OBJECT

  private slots:
    void honorsXdgAndExplicitOverrides();
    void usesPathKeyFallback();
    void rejectsUnsafeProfileNamesByFallingBack();
};

void ClavisPathsTest::honorsXdgAndExplicitOverrides()
{
    QTemporaryDir temporary;
    QVERIFY(temporary.isValid());
    const QString root = temporary.path();
    for (const char *name : {
             "CLAVIS_CONFIG_HOME",
             "CLAVIS_DATA_HOME",
             "CLAVIS_STATE_HOME",
             "CLAVIS_CACHE_HOME",
             "CLAVIS_RUNTIME_HOME",
         }) {
        qunsetenv(name);
    }
    qputenv("HOME", QFile::encodeName(QDir(root).filePath(QStringLiteral("home"))));
    qputenv("XDG_CONFIG_HOME", QFile::encodeName(QDir(root).filePath(QStringLiteral("config"))));
    qputenv("XDG_DATA_HOME", QFile::encodeName(QDir(root).filePath(QStringLiteral("data"))));
    qputenv("XDG_STATE_HOME", QFile::encodeName(QDir(root).filePath(QStringLiteral("state"))));
    qputenv("XDG_CACHE_HOME", QFile::encodeName(QDir(root).filePath(QStringLiteral("cache"))));
    qputenv("XDG_RUNTIME_DIR", QFile::encodeName(QDir(root).filePath(QStringLiteral("runtime"))));
    qputenv("CLAVIS_PROFILE", "test-profile");
    qputenv("CLAVIS_PROFILE_CONFIG_HOME",
            QFile::encodeName(QDir(root).filePath(QStringLiteral("profile-config"))));
    qputenv("CLAVIS_PROFILE_HOME", QFile::encodeName(QDir(root).filePath(QStringLiteral("profile"))));
    qputenv("CLAVIS_GENERATED_HOME", QFile::encodeName(QDir(root).filePath(QStringLiteral("generated"))));
    qputenv("CLAVIS_KEY", QFile::encodeName(QDir(root).filePath(QStringLiteral("system-bin/key"))));

    QCOMPARE(qgetenv("XDG_CONFIG_HOME"), QFile::encodeName(QDir(root).filePath(QStringLiteral("config"))));

    const auto paths = Clavis::Runtime::ClavisPaths::fromEnvironment();
    QCOMPARE(paths.configHome(), QDir(root).filePath(QStringLiteral("config/clavis")));
    QCOMPARE(paths.dataHome(), QDir(root).filePath(QStringLiteral("data/clavis")));
    QCOMPARE(paths.stateHome(), QDir(root).filePath(QStringLiteral("state/clavis")));
    QCOMPARE(paths.cacheHome(), QDir(root).filePath(QStringLiteral("cache/clavis")));
    QCOMPARE(paths.runtimeHome(), QDir(root).filePath(QStringLiteral("runtime/clavis")));
    QCOMPARE(paths.profileName(), QStringLiteral("test-profile"));
    QCOMPARE(paths.profileConfigHome(), QDir(root).filePath(QStringLiteral("profile-config")));
    QCOMPARE(paths.profileHome(), QDir(root).filePath(QStringLiteral("profile")));
    QCOMPARE(paths.generatedHome(), QDir(root).filePath(QStringLiteral("generated")));
    QCOMPARE(paths.stableKey(), QDir(root).filePath(QStringLiteral("system-bin/key")));
}

void ClavisPathsTest::usesPathKeyFallback()
{
    qunsetenv("CLAVIS_KEY");
    qputenv("CLAVIS_BIN_HOME", "/tmp/obsolete-clavis-bin");

    const auto paths = Clavis::Runtime::ClavisPaths::fromEnvironment();
    QCOMPARE(paths.stableKey(), QStringLiteral("key"));
}

void ClavisPathsTest::rejectsUnsafeProfileNamesByFallingBack()
{
    qputenv("CLAVIS_PROFILE", "../escape");
    qunsetenv("CLAVIS_PROFILE_HOME");
    qunsetenv("CLAVIS_PROFILE_CONFIG_HOME");
    qunsetenv("CLAVIS_GENERATED_HOME");
    const auto paths = Clavis::Runtime::ClavisPaths::fromEnvironment();
    QCOMPARE(paths.profileName(), QStringLiteral("default"));
    QVERIFY(paths.profileHome().endsWith(QStringLiteral("/profiles/default")));

    qputenv("CLAVIS_PROFILE", "bad\\name");
    QCOMPARE(Clavis::Runtime::ClavisPaths::fromEnvironment().profileName(), QStringLiteral("default"));
}

QTEST_MAIN(ClavisPathsTest)

#include "clavis_paths_test.moc"
