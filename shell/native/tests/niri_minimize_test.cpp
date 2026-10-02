#include "niri_plugin.h"
#include "niri_animation_targets.h"
#include <QJsonArray>
#include <QJsonDocument>
#include <QElapsedTimer>
#include <QLocalServer>
#include <QPointer>
#include <QTemporaryDir>
#include <QThread>
#include <QTimer>
#include <QUuid>
#include <QtTest>

// A real local IPC peer runs on another thread, including synchronous action replies.
class NiriPeer : public QObject {
  public:
    QLocalServer *server = nullptr;
    QPointer<QLocalSocket> events;
    QPointer<QLocalSocket> targetPublisher;
    int targetConnections = 0;
    QList<QJsonValue> requests;
    QJsonObject capabilityReply{
        {"Ok", QJsonObject{{"Capabilities", QJsonObject{{"window_minimization", true}}}}}};
    int capabilityDelay = 0;
    int moveDelay = 0;
    bool dropMoveReply = false;
    double minimumX = -10000;
    double maximumX = 10000;
    QJsonArray windows{QJsonObject{{"id", 42},
                                   {"title", "Same title"},
                                   {"app_id", "test.editor"},
                                   {"workspace_id", QJsonValue()},
                                   {"is_minimized", true}}};
    void listen(const QString &path)
    {
        server = new QLocalServer(this);
        if (!server->listen(path))
            qFatal("Cannot open test IPC socket");
        connect(server, &QLocalServer::newConnection, this, [this] {
            while (server->hasPendingConnections()) {
                auto *peer = server->nextPendingConnection();
                connect(peer, &QLocalSocket::readyRead, peer, [this, peer] {
                    while (peer->canReadLine()) {
                        const auto request =
                            QJsonDocument::fromJson("[" + peer->readLine().trimmed() + "]").array().at(0);
                        requests.append(request);
                        if (request == QJsonValue("EventStream")) {
                            events = peer;
                            peer->write("{\"Ok\":\"Handled\"}\n");
                        } else if (request == QJsonValue("Capabilities")) {
                            const auto reply =
                                QJsonDocument(capabilityReply).toJson(QJsonDocument::Compact) + '\n';
                            QTimer::singleShot(capabilityDelay, peer, [peer, reply] { peer->write(reply); });
                        } else if (request == QJsonValue("Windows")) {
                            peer->write(QJsonDocument(QJsonObject{{"Ok", QJsonObject{{"Windows", windows}}}})
                                            .toJson(QJsonDocument::Compact) +
                                        '\n');
                        } else if (request == QJsonValue("Workspaces")) {
                            peer->write("{\"Ok\":{\"Workspaces\":[]}}\n");
                        } else if (request == QJsonValue("Outputs")) {
                            peer->write("{\"Ok\":{\"Outputs\":{\"DP-2\":{\"current_mode\":0}}}}\n");
                        } else if (request.toObject().value("Action").toObject().contains(
                                       "MoveFloatingWindow")) {
                            const auto move = request.toObject()
                                                  .value("Action")
                                                  .toObject()
                                                  .value("MoveFloatingWindow")
                                                  .toObject();
                            for (qsizetype i = 0; i < windows.size(); ++i) {
                                auto window = windows.at(i).toObject();
                                if (window.value("id") != move.value("id") ||
                                    !window.value("is_floating").toBool() ||
                                    window.value("is_minimized").toBool())
                                    continue;
                                auto layout = window.value("layout").toObject();
                                auto position = layout.value("tile_pos_in_workspace_view").toArray();
                                position[0] =
                                    qBound(minimumX,
                                           position.at(0).toDouble() +
                                               move.value("x").toObject().value("AdjustFixed").toDouble(),
                                           maximumX);
                                layout["tile_pos_in_workspace_view"] = position;
                                window["layout"] = layout;
                                windows[i] = window;
                                send({{"WindowOpenedOrChanged", QJsonObject{{"window", window}}}});
                            }
                            if (dropMoveReply)
                                peer->disconnectFromServer();
                            else
                                QTimer::singleShot(moveDelay, peer,
                                                   [peer] { peer->write("{\"Ok\":\"Handled\"}\n"); });
                        } else {
                            if (request.toObject().contains("SetWindowAnimationTargets") &&
                                targetPublisher != peer) {
                                targetPublisher = peer;
                                ++targetConnections;
                            }
                            peer->write("{\"Ok\":\"Handled\"}\n");
                        }
                    }
                });
            }
        });
    }
    void send(const QJsonObject &event)
    {
        if (events)
            events->write(QJsonDocument(event).toJson(QJsonDocument::Compact) + '\n');
    }
};

class NiriMinimizeTest : public QObject {
    Q_OBJECT
    QTemporaryDir m_directory;
    QThread m_thread;
    NiriPeer *m_peer = nullptr;
    QByteArray m_oldSocket;
    void server(const std::function<void(NiriPeer *)> &function)
    {
        QMetaObject::invokeMethod(m_peer, [&] { function(m_peer); }, Qt::BlockingQueuedConnection);
    }
    static QJsonObject floatingWindow(int id, double x, int workspace = 7)
    {
        return {{"id", id},
                {"workspace_id", workspace},
                {"is_floating", true},
                {"layout", QJsonObject{{"tile_pos_in_workspace_view", QJsonArray{x, 100}}}}};
    }
    double position(int id)
    {
        double result = -10000;
        server([&](auto *peer) {
            for (const auto &entry : peer->windows) {
                const auto window = entry.toObject();
                if (window.value("id").toInt() == id)
                    result = window.value("layout")
                                 .toObject()
                                 .value("tile_pos_in_workspace_view")
                                 .toArray()
                                 .at(0)
                                 .toDouble();
            }
        });
        return result;
    }
    int moveCount()
    {
        int result = 0;
        server([&](auto *peer) {
            for (const auto &request : peer->requests)
                result += request.toObject().value("Action").toObject().contains("MoveFloatingWindow");
        });
        return result;
    }
  private slots:
    void init()
    {
        m_oldSocket = qgetenv("NIRI_SOCKET");
        m_peer = new NiriPeer;
        m_peer->moveToThread(&m_thread);
        m_thread.start();
        const auto socket = m_directory.filePath(QUuid::createUuid().toString(QUuid::Id128));
        server([&](auto *peer) { peer->listen(socket); });
        qputenv("NIRI_SOCKET", socket.toUtf8());
    }
    void cleanup()
    {
        server([](auto *peer) { delete peer; });
        m_peer = nullptr;
        m_thread.quit();
        m_thread.wait();
        qputenv("NIRI_SOCKET", m_oldSocket);
    }
    void floatingParallaxIsAsyncCoalescedAndClamped()
    {
        server([](auto *peer) {
            auto tiled = floatingWindow(43, 200);
            tiled["is_floating"] = false;
            auto minimized = floatingWindow(44, 300);
            minimized["is_minimized"] = true;
            peer->windows = {floatingWindow(42, 100), tiled, minimized};
            peer->maximumX = 120;
            peer->moveDelay = 150;
        });
        NiriPlugin niri;
        QTRY_VERIFY(niri.connected());
        QTRY_COMPARE(niri.windows()->rowCount(), 3);
        QElapsedTimer elapsed;
        elapsed.start();
        niri.setFloatingParallaxOffsets({{"7", 96}});
        QVERIFY(elapsed.elapsed() < 80);
        QTRY_COMPARE(position(42), 120.0);
        // Change direction before the slow reply. Only the latest target is sent.
        niri.setFloatingParallaxOffsets({{"7", -96}});
        niri.setFloatingParallaxOffsets({});
        QTRY_COMPARE(position(42), 100.0);
        QTest::qWait(180);
        QCOMPARE(moveCount(), 2);
        QCOMPARE(position(43), 200.0);
        QCOMPARE(position(44), 300.0);
        server([](auto *peer) {
            for (const auto &request : peer->requests) {
                const auto action = request.toObject().value("Action").toObject();
                if (action.isEmpty())
                    continue;
                QCOMPARE(action.keys(), QStringList{"MoveFloatingWindow"});
                const auto move = action.value("MoveFloatingWindow").toObject();
                QCOMPARE(move.value("id").toInt(), 42);
                QCOMPARE(move.value("y").toObject().value("AdjustFixed").toDouble(), 0.0);
            }
        });
    }
    void floatingParallaxPreservesUserMoveAndSuspendsTiledWindows()
    {
        server([](auto *peer) { peer->windows = {floatingWindow(42, 100)}; });
        NiriPlugin niri;
        QTRY_COMPARE(niri.windows()->rowCount(), 1);
        niri.setFloatingParallaxOffsets({{"7", 40}});
        QTRY_COMPARE(position(42), 140.0);
        QTest::qWait(30);
        server([](auto *peer) {
            auto moved = floatingWindow(42, 190);
            peer->windows = {moved};
            peer->send({{"WindowOpenedOrChanged", QJsonObject{{"window", moved}}}});
        });
        niri.setFloatingParallaxOffsets({});
        QTRY_COMPARE(position(42), 150.0);
        QTest::qWait(30);
        niri.setFloatingParallaxOffsets({{"7", 40}});
        QTRY_COMPARE(position(42), 190.0);
        QTest::qWait(30);
        server([](auto *peer) {
            auto tiled = floatingWindow(42, 190);
            tiled["is_floating"] = false;
            peer->windows = {tiled};
            peer->send({{"WindowOpenedOrChanged", QJsonObject{{"window", tiled}}}});
        });
        QTRY_VERIFY(!niri.windowById(42).value("isFloating").toBool());
        niri.setFloatingParallaxOffsets({});
        QTest::qWait(50);
        QCOMPARE(moveCount(), 3);
        server([](auto *peer) {
            auto restored = floatingWindow(42, 190, 8);
            peer->windows = {restored};
            peer->send({{"WindowOpenedOrChanged", QJsonObject{{"window", restored}}}});
        });
        QTRY_COMPARE(position(42), 150.0);
        QTest::qWait(30);
        QCOMPARE(moveCount(), 4);
    }
    void floatingParallaxReloadReleasesSettledOffset()
    {
        server([](auto *peer) { peer->windows = {floatingWindow(42, 100)}; });
        auto *niri = new NiriPlugin;
        QTRY_COMPARE(niri->windows()->rowCount(), 1);
        niri->setFloatingParallaxOffsets({{"7", 40}});
        QTRY_COMPARE(position(42), 140.0);
        QTest::qWait(30);
        delete niri;
        QTRY_COMPARE(position(42), 100.0);
    }
    void floatingParallaxMeasuresEvenWhenMoveReplyIsLost()
    {
        server([](auto *peer) {
            peer->windows = {floatingWindow(42, 100)};
            peer->dropMoveReply = true;
        });
        NiriPlugin niri;
        QTRY_COMPARE(niri.windows()->rowCount(), 1);
        niri.setFloatingParallaxOffsets({{"7", 40}});
        QTRY_COMPARE(position(42), 140.0);
        QTest::qWait(30);
        niri.setFloatingParallaxOffsets({});
        QTRY_COMPARE(position(42), 100.0);
        QTest::qWait(30);
        QCOMPARE(moveCount(), 2);
    }
    void floatingParallaxReloadSharesPendingLedger()
    {
        server([](auto *peer) {
            peer->windows = {floatingWindow(42, 100)};
            peer->moveDelay = 150;
        });
        auto *oldEngine = new NiriPlugin;
        QTRY_COMPARE(oldEngine->windows()->rowCount(), 1);
        oldEngine->setFloatingParallaxOffsets({{"7", 40}});
        QTRY_COMPARE(position(42), 140.0);
        // Acquire the new engine before releasing the old one. Its ownership
        // prevents the old destructor from overwriting the new target with zero.
        NiriPlugin newEngine;
        QTRY_COMPARE(newEngine.windows()->rowCount(), 1);
        newEngine.setFloatingParallaxOffsets({{"7", 60}});
        delete oldEngine;
        QTRY_COMPARE(position(42), 160.0);
        QTest::qWait(180);
        newEngine.setFloatingParallaxOffsets({});
        QTRY_COMPARE(position(42), 100.0);
        QTest::qWait(180);
        QCOMPARE(moveCount(), 3);
    }
    void floatingParallaxReconnectRejectsOldReplies()
    {
        server([](auto *peer) {
            peer->windows = {floatingWindow(42, 100)};
            peer->moveDelay = 250;
        });
        NiriPlugin niri;
        QTRY_COMPARE(niri.windows()->rowCount(), 1);
        niri.setFloatingParallaxOffsets({{"7", 40}});
        QTRY_COMPARE(position(42), 140.0);
        const auto generation = niri.connectionGeneration();
        server([](auto *peer) { peer->events->abort(); });
        QTRY_VERIFY(!niri.connected());
        niri.setFloatingParallaxOffsets({});
        QVERIFY(niri.connectToNiri());
        QVERIFY(niri.connectionGeneration() > generation);
        QTRY_COMPARE(position(42), 100.0);
        QTest::qWait(300);
        QCOMPARE(moveCount(), 2);
        QCOMPARE(position(42), 100.0);
    }
    void floatingParallaxDropsUnrestorableResidualAtZero()
    {
        server([](auto *peer) {
            peer->windows = {floatingWindow(42, 100)};
            peer->minimumX = 0;
        });
        NiriPlugin niri;
        QTRY_COMPARE(niri.windows()->rowCount(), 1);
        niri.setFloatingParallaxOffsets({{"7", 40}});
        QTRY_COMPARE(position(42), 140.0);
        QTest::qWait(30);
        server([](auto *peer) {
            const auto window = floatingWindow(42, 0);
            peer->windows = {window};
            peer->send({{"WindowOpenedOrChanged", QJsonObject{{"window", window}}}});
        });
        niri.setFloatingParallaxOffsets({});
        QTRY_COMPARE(moveCount(), 2);
        QTest::qWait(30);
        niri.setFloatingParallaxOffsets({{"7", 40}});
        QTRY_COMPARE(position(42), 40.0);
        niri.setFloatingParallaxOffsets({});
        QTRY_COMPARE(position(42), 0.0);
    }
    void targetsUseOneAsyncConnectionAndReleaseOnDisable()
    {
        NiriAnimationTargets publisher;
        const QVariantMap target{{"id", 42},
                                 {"output", "DP-2"},
                                 {"edge", "left"},
                                 {"rect", QVariantList{8.5, 120.25, 40.0, 40.0}}};
        publisher.setTargets({target});
        publisher.setEnabled(true);
        int count = 0;
        QTRY_VERIFY(([&] {
            server([&](auto *peer) { count = peer->requests.size(); });
            return count == 1;
        })());
        publisher.setTargets({target});
        QTest::qWait(80);
        publisher.setTargets({});
        QTRY_VERIFY(([&] {
            server([&](auto *peer) { count = peer->requests.size(); });
            return count == 2;
        })());
        server([&](auto *peer) {
            QCOMPARE(peer->targetConnections, 1);
            const auto first =
                peer->requests.first().toObject().value("SetWindowAnimationTargets").toObject();
            QCOMPARE(
                first.value("targets").toArray().at(0).toObject().value("rect").toArray().at(0).toDouble(),
                8.5);
            QVERIFY(peer->requests.last()
                        .toObject()
                        .value("SetWindowAnimationTargets")
                        .toObject()
                        .value("targets")
                        .toArray()
                        .isEmpty());
        });
        publisher.setEnabled(false);
        bool disconnected = false;
        QTRY_VERIFY(([&] {
            server([&](auto *peer) {
                disconnected = peer->targetPublisher->state() == QLocalSocket::UnconnectedState;
            });
            return disconnected;
        })());
    }
    void separateAnimationCapabilityIsOptional()
    {
        NiriPlugin legacy;
        QTRY_VERIFY(legacy.supportsMinimize());
        QVERIFY(!legacy.supportsMinimizeAnimation());
        QVERIFY(legacy.minimizeEffects().isEmpty());
        server([](auto *peer) {
            peer->capabilityReply = {
                {"Ok", QJsonObject{{"Capabilities", QJsonObject{{"window_minimization", true},
                                                                {"window_minimization_animation", true}}}}}};
        });
        NiriPlugin animated;
        QTRY_VERIFY(animated.supportsMinimizeAnimation());
        QVERIFY(animated.minimizeEffects().isEmpty());
        server([](auto *peer) {
            peer->capabilityReply = {
                {"Ok", QJsonObject{{"Capabilities",
                                    QJsonObject{{"window_minimization", true},
                                                {"window_minimization_animation", true},
                                                {"window_minimization_effects",
                                                 QJsonArray{"scale", "genie", "genie", "unknown"}}}}}}};
        });
        NiriPlugin selectable;
        QTRY_COMPARE(selectable.minimizeEffects(), (QStringList{"scale", "genie"}));
    }
    void snapshotEventsAndOutputActions()
    {
        NiriPlugin niri;
        QTRY_VERIFY(niri.supportsMinimize());
        QTRY_COMPARE(niri.outputSnapshot().size(), 1);
        QVERIFY(niri.windowById(42).value("isMinimized").toBool());
        QVERIFY(niri.searchWindows("").at(0).toMap().value("isMinimized").toBool());
        QCOMPARE(niri.windows()->data(niri.windows()->index(0), NiriWindowModel::IsMinimizedRole).toBool(),
                 true);
        QVERIFY(!niri.restoreWindow(42, "gone-output"));
        QVERIFY(niri.restoreWindow(42, "DP-2"));
        QVERIFY(niri.minimizeWindow(42));
        server([&](auto *peer) {
            QCOMPARE(peer->requests.count(QJsonValue("Capabilities")), 1);
            const QJsonValue restore(QJsonObject{
                {"Action", QJsonObject{{"RestoreWindow", QJsonObject{{"id", 42}, {"output", "DP-2"}}}}}});
            const QJsonValue minimize(
                QJsonObject{{"Action", QJsonObject{{"MinimizeWindow", QJsonObject{{"id", 42}}}}}});
            QVERIFY(peer->requests.contains(restore));
            QVERIFY(peer->requests.contains(minimize));
            peer->send(
                {{"WindowOpenedOrChanged", QJsonObject{{"window", QJsonObject{{"id", 42},
                                                                              {"title", "Restored"},
                                                                              {"is_focused", true},
                                                                              {"workspace_id", 7}}}}}});
        });
        QTRY_COMPARE(niri.windowById(42).value("title").toString(), QString("Restored"));
        QVERIFY(!niri.windowById(42).value("isMinimized").toBool());
        QVERIFY(!niri.focusedWindow().value("isMinimized").toBool());
        server([](auto *peer) { peer->send({{"WindowClosed", QJsonObject{{"id", 42}}}}); });
        QTRY_COMPARE(niri.windows()->rowCount(), 0);
        QVERIFY(!niri.restoreWindow(42, "DP-2"));
    }
    void legacyCapabilityIsQuietAndDoesNotProbeWithActions()
    {
        server([](auto *peer) { peer->capabilityReply = {{"Err", "unknown variant Capabilities"}}; });
        NiriPlugin niri;
        QTRY_VERIFY(niri.connected());
        QTest::qWait(80);
        QVERIFY(!niri.supportsMinimize());
        QVERIFY(niri.lastError().isEmpty());
        QVERIFY(!niri.minimizeWindow(42));
        QVERIFY(!niri.restoreWindow(42, "DP-2"));
        server([](auto *peer) {
            QCOMPARE(peer->requests.count(QJsonValue("Capabilities")), 1);
            for (const auto &request : peer->requests)
                QVERIFY(!request.toObject().contains("Action"));
        });
    }
    void delayedCapabilityReplyCannotCrossReconnect()
    {
        server([](auto *peer) { peer->capabilityDelay = 250; });
        NiriPlugin niri;
        QTRY_VERIFY(niri.connected());
        QTest::qWait(40);
        const auto generation = niri.connectionGeneration();
        server([](auto *peer) {
            peer->events->abort();
            peer->capabilityDelay = 0;
            peer->capabilityReply = {
                {"Ok", QJsonObject{{"Capabilities", QJsonObject{{"window_minimization", false}}}}}};
        });
        QTRY_VERIFY(!niri.connected());
        QVERIFY(!niri.supportsMinimize());
        QCOMPARE(niri.windows()->rowCount(), 0);
        QVERIFY(niri.connectToNiri());
        QVERIFY(niri.connectionGeneration() > generation);
        QTest::qWait(350);
        QVERIFY(!niri.supportsMinimize());
        server([](auto *peer) { QCOMPARE(peer->requests.count(QJsonValue("Capabilities")), 2); });
    }
};
QTEST_GUILESS_MAIN(NiriMinimizeTest)
#include "niri_minimize_test.moc"
