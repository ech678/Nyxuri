#include "process_quit.h"
#include <QProcess>
#include <QtTest>
#include <unistd.h>

class ProcessQuitTest : public QObject {
    Q_OBJECT
  private slots:
    void confirmationAndDeduplication()
    {
        QProcess child;
        child.start("sleep", {"30"});
        QVERIFY(child.waitForStarted());
        ProcessQuit quit;
        const auto pid = child.processId();
        QVERIFY(quit.prepare({pid, pid}));
        QVERIFY(!child.waitForFinished(20));
        QVERIFY(quit.confirm());
        QVERIFY(child.waitForFinished());
        QCOMPARE(child.exitStatus(), QProcess::CrashExit);
        QVERIFY(!quit.confirm());
    }
    void cancellationAndValidation()
    {
        QProcess child;
        child.start("sleep", {"30"});
        QVERIFY(child.waitForStarted());
        ProcessQuit quit;
        QVERIFY(quit.prepare({child.processId()}));
        quit.cancel();
        QVERIFY(!quit.confirm());
        QVERIFY(!quit.prepare({child.processId(), -1}));
        QVERIFY(!quit.confirm());
        QVERIFY(!quit.prepare({getpid()}));
        QVERIFY(!child.waitForFinished(20));
        child.kill();
        QVERIFY(child.waitForFinished());
    }
    void exitDuringConfirmation()
    {
        QProcess child;
        child.start("sleep", {"30"});
        QVERIFY(child.waitForStarted());
        ProcessQuit quit;
        QVERIFY(quit.prepare({child.processId()}));
        child.kill();
        QVERIFY(child.waitForFinished());
        QVERIFY(quit.confirm());
    }
};
QTEST_GUILESS_MAIN(ProcessQuitTest)
#include "process_quit_test.moc"
