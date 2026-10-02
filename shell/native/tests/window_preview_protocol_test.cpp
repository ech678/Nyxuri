#include "window_preview_manager.h"
#include "ext-foreign-toplevel-list-v1-server-protocol.h"
#include "ext-image-capture-source-v1-server-protocol.h"
#include "ext-image-copy-capture-v1-server-protocol.h"
#include <QSocketNotifier>
#include <QTemporaryDir>
#include <QtTest>
#include <algorithm>
#include <cstring>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <wayland-server.h>

// A small real protocol peer, with no compositor process or sibling repository.
// Both sides use the Qt event loop; every capture passes through a wl_shm buffer.
class CaptureServer : public QObject {
    struct Resource {
        CaptureServer *server;
        QString id;
        wl_resource *buffer = nullptr;
    };
    wl_display *m_display = nullptr;
    QSocketNotifier *m_notifier = nullptr;
    QTemporaryDir m_directory;
    QHash<wl_resource *, QString> m_handles;
    QSet<wl_resource *> m_sessions;
    static Resource *data(wl_resource *resource)
    {
        return static_cast<Resource *>(wl_resource_get_user_data(resource));
    }
    static void destroy(wl_client *, wl_resource *resource) { wl_resource_destroy(resource); }
    wl_resource *make(wl_client *client, uint32_t id, const wl_interface *interface,
                      const void *implementation, const QString &window = {})
    {
        auto *resource = wl_resource_create(client, interface, 1, id);
        wl_resource_set_implementation(resource, implementation, new Resource{this, window},
                                       [](wl_resource *resource) {
                                           auto *d = data(resource);
                                           d->server->m_handles.remove(resource);
                                           d->server->m_sessions.remove(resource);
                                           delete d;
                                       });
        return resource;
    }
    static const struct ext_foreign_toplevel_handle_v1_interface handleImplementation;
    static const struct ext_foreign_toplevel_list_v1_interface listImplementation;
    static const struct ext_image_capture_source_v1_interface sourceImplementation;
    static const struct ext_foreign_toplevel_image_capture_source_manager_v1_interface sourcesImplementation;
    static const struct ext_image_copy_capture_manager_v1_interface managerImplementation;
    static const struct ext_image_copy_capture_session_v1_interface sessionImplementation;
    static const struct ext_image_copy_capture_frame_v1_interface frameImplementation;

  public:
    QString path;
    QHash<QString, QRgb> colors{{"42", qRgb(255, 0, 0)}, {"43", qRgb(0, 0, 255)}};
    QHash<QString, int> captures;
    int peakSessions = 0;
    bool stalled = false;
    int failure = -1;
    CaptureServer()
    {
        m_display = wl_display_create();
        if (!m_display || wl_display_init_shm(m_display) < 0)
            qFatal("Cannot initialize private Wayland test display");
        path = m_directory.filePath("wayland-test");
        const int socket = ::socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
        sockaddr_un address{};
        address.sun_family = AF_UNIX;
        const auto bytes = path.toUtf8();
        if (bytes.size() >= qsizetype(sizeof(address.sun_path)))
            qFatal("Test socket path too long");
        std::memcpy(address.sun_path, bytes.constData(), bytes.size());
        if (socket < 0 || ::bind(socket, reinterpret_cast<sockaddr *>(&address), sizeof(address)) < 0 ||
            ::listen(socket, 16) < 0 || wl_display_add_socket_fd(m_display, socket) < 0)
            qFatal("Cannot listen on private Wayland test socket");
        wl_global_create(
            m_display, &ext_foreign_toplevel_list_v1_interface, 1, this,
            [](wl_client *client, void *owner, uint32_t, uint32_t id) {
                auto *s = static_cast<CaptureServer *>(owner);
                auto *list =
                    s->make(client, id, &ext_foreign_toplevel_list_v1_interface, &listImplementation);
                for (const auto &window : s->colors.keys()) {
                    auto *handle = s->make(client, 0, &ext_foreign_toplevel_handle_v1_interface,
                                           &handleImplementation, window);
                    s->m_handles.insert(handle, window);
                    ext_foreign_toplevel_list_v1_send_toplevel(list, handle);
                    ext_foreign_toplevel_handle_v1_send_identifier(handle, window.toUtf8().constData());
                    ext_foreign_toplevel_handle_v1_send_title(handle, "Same title");
                    ext_foreign_toplevel_handle_v1_send_app_id(handle, "test.editor");
                    ext_foreign_toplevel_handle_v1_send_done(handle);
                }
            });
        wl_global_create(m_display, &ext_foreign_toplevel_image_capture_source_manager_v1_interface, 1, this,
                         [](wl_client *client, void *owner, uint32_t, uint32_t id) {
                             static_cast<CaptureServer *>(owner)->make(
                                 client, id, &ext_foreign_toplevel_image_capture_source_manager_v1_interface,
                                 &sourcesImplementation);
                         });
        wl_global_create(m_display, &ext_image_copy_capture_manager_v1_interface, 1, this,
                         [](wl_client *client, void *owner, uint32_t, uint32_t id) {
                             static_cast<CaptureServer *>(owner)->make(
                                 client, id, &ext_image_copy_capture_manager_v1_interface,
                                 &managerImplementation);
                         });
        auto *loop = wl_display_get_event_loop(m_display);
        m_notifier = new QSocketNotifier(wl_event_loop_get_fd(loop), QSocketNotifier::Read, this);
        connect(m_notifier, &QSocketNotifier::activated, this, [this, loop] {
            wl_event_loop_dispatch(loop, 0);
            flush();
        });
    }
    ~CaptureServer() override
    {
        delete m_notifier;
        wl_display_destroy_clients(m_display);
        wl_display_destroy(m_display);
    }
    int sessions() const { return m_sessions.size(); }
    void flush() { wl_display_flush_clients(m_display); }
    void closeWindow(const QString &id)
    {
        colors.remove(id);
        for (auto it = m_handles.cbegin(); it != m_handles.cend(); ++it)
            if (it.value() == id)
                ext_foreign_toplevel_handle_v1_send_closed(it.key());
        flush();
    }
    void revoke()
    {
        for (auto *session : m_sessions)
            ext_image_copy_capture_session_v1_send_stopped(session);
        flush();
    }
    void disconnectClients() { wl_display_destroy_clients(m_display); }
};
const struct ext_foreign_toplevel_handle_v1_interface CaptureServer::handleImplementation = {destroy};
const struct ext_foreign_toplevel_list_v1_interface CaptureServer::listImplementation = {
    [](wl_client *, wl_resource *resource) { ext_foreign_toplevel_list_v1_send_finished(resource); },
    destroy};
const struct ext_image_capture_source_v1_interface CaptureServer::sourceImplementation = {destroy};
const struct ext_foreign_toplevel_image_capture_source_manager_v1_interface
    CaptureServer::sourcesImplementation = {
        [](wl_client *client, wl_resource *resource, uint32_t id, wl_resource *handle) {
            data(resource)->server->make(client, id, &ext_image_capture_source_v1_interface,
                                         &sourceImplementation, data(handle)->id);
        },
        destroy};
const struct ext_image_copy_capture_manager_v1_interface CaptureServer::managerImplementation = {
    [](wl_client *client, wl_resource *resource, uint32_t id, wl_resource *source, uint32_t) {
        auto *server = data(resource)->server;
        auto *session = server->make(client, id, &ext_image_copy_capture_session_v1_interface,
                                     &sessionImplementation, data(source)->id);
        server->m_sessions.insert(session);
        server->peakSessions = std::max(server->peakSessions, server->sessions());
        ext_image_copy_capture_session_v1_send_buffer_size(session, 64, 48);
        ext_image_copy_capture_session_v1_send_shm_format(session, WL_SHM_FORMAT_ARGB8888);
        ext_image_copy_capture_session_v1_send_done(session);
    },
    [](wl_client *, wl_resource *, uint32_t, wl_resource *, wl_resource *) {
        qFatal("Unexpected cursor capture");
    },
    destroy};
const struct ext_image_copy_capture_session_v1_interface CaptureServer::sessionImplementation = {
    [](wl_client *client, wl_resource *resource, uint32_t id) {
        auto *d = data(resource);
        d->server->make(client, id, &ext_image_copy_capture_frame_v1_interface, &frameImplementation, d->id);
    },
    destroy};
const struct ext_image_copy_capture_frame_v1_interface CaptureServer::frameImplementation = {
    destroy, [](wl_client *, wl_resource *resource, wl_resource *buffer) { data(resource)->buffer = buffer; },
    [](wl_client *, wl_resource *, int32_t, int32_t, int32_t, int32_t) {},
    [](wl_client *, wl_resource *resource) {
        auto *d = data(resource);
        auto *s = d->server;
        ++s->captures[d->id];
        if (s->stalled)
            return;
        if (s->failure >= 0) {
            ext_image_copy_capture_frame_v1_send_failed(resource, uint32_t(s->failure));
            return;
        }
        auto *shm = wl_shm_buffer_get(d->buffer);
        if (!shm)
            qFatal("Capture did not attach a SHM buffer");
        wl_shm_buffer_begin_access(shm);
        auto *pixels = static_cast<QRgb *>(wl_shm_buffer_get_data(shm));
        std::fill_n(pixels, 64 * 48, s->colors.value(d->id));
        wl_shm_buffer_end_access(shm);
        ext_image_copy_capture_frame_v1_send_transform(resource, WL_OUTPUT_TRANSFORM_NORMAL);
        ext_image_copy_capture_frame_v1_send_ready(resource);
    }};

class WindowPreviewProtocolTest : public QObject {
    Q_OBJECT
  private slots:
    void releaseMinimizeRestoreAndClose()
    {
        CaptureServer server;
        WindowPreviewManager manager;
        manager.open(server.path);
        manager.setWindows({"42", "43"}, {});
        QTRY_VERIFY(manager.frameFor("42")->hasFrame() && manager.frameFor("43")->hasFrame());
        QTRY_COMPARE(manager.captureCount(), 0);
        QTRY_COMPARE(server.sessions(), 0);
        QCOMPARE(server.peakSessions, 1);
        QCOMPARE(manager.frameFor("42")->image().pixelColor(0, 0), QColor(Qt::red));
        QCOMPARE(manager.frameFor("43")->image().pixelColor(0, 0), QColor(Qt::blue));
        manager.setTargets("hover", {"42"});
        QTRY_COMPARE(server.sessions(), 1);
        manager.release("hover");
        QTRY_COMPARE(manager.captureCount(), 0);
        QTRY_COMPARE(server.sessions(), 0);
        QVERIFY(manager.frameFor("42")->hasFrame());
        manager.setWindows({"42", "43"}, {"42"});
        manager.setTargets("hover", {"42"});
        const auto count = server.captures.value("42");
        QTest::qWait(120);
        QCOMPARE(server.captures.value("42"), count);
        QCOMPARE(manager.captureCount(), 0);
        QVERIFY(manager.frameFor("42")->hasFrame());
        server.stalled = true;
        manager.setWindows({"42", "43"}, {});
        QTRY_VERIFY(server.captures.value("42") > count);
        QCOMPARE(manager.frameFor("42")->image().pixelColor(0, 0), QColor(Qt::red));
        manager.release("hover");
        QTRY_COMPARE(server.sessions(), 0);
        server.stalled = false;
        server.colors["42"] = qRgb(0, 255, 0);
        manager.setTargets("hover", {"42"});
        QTRY_COMPARE(manager.frameFor("42")->image().pixelColor(0, 0), QColor(Qt::green));
        QPointer<WindowPreviewFrame> old = manager.frameFor("42");
        server.closeWindow("42");
        QTRY_VERIFY(!old || !old->hasFrame());
        manager.setWindows({"43"}, {});
        QVERIFY(!manager.frameFor("42"));
        QVERIFY(manager.frameFor("43")->hasFrame());
    }
    void failurePreservesPixelsButRevocationAndDisconnectClear()
    {
        CaptureServer server;
        WindowPreviewManager manager;
        manager.open(server.path);
        manager.setWindows({"42"}, {});
        QTRY_VERIFY(manager.frameFor("42")->hasFrame());
        QTRY_COMPARE(server.sessions(), 0);
        server.failure = EXT_IMAGE_COPY_CAPTURE_FRAME_V1_FAILURE_REASON_UNKNOWN;
        manager.setTargets("hover", {"42"});
        QTRY_VERIFY(manager.captureFor("42") && !manager.captureFor("42")->error().isEmpty());
        QVERIFY(manager.frameFor("42")->hasFrame());
        manager.release("hover");
        QTRY_COMPARE(manager.captureCount(), 0);
        server.failure = -1;
        manager.setTargets("hover", {"42"});
        QTRY_COMPARE(server.sessions(), 1);
        server.revoke();
        QTRY_VERIFY(!manager.frameFor("42")->hasFrame());
        manager.release("hover");
        QTRY_COMPARE(manager.captureCount(), 0);
        manager.setTargets("hover", {"42"});
        QTRY_VERIFY(manager.frameFor("42")->hasFrame());
        QPointer<WindowPreviewFrame> beforeDisconnect = manager.frameFor("42");
        server.disconnectClients();
        QTRY_VERIFY(!beforeDisconnect || !beforeDisconnect->hasFrame());
        QTRY_VERIFY(!manager.supported());
        manager.open(server.path);
        manager.setWindows({"42"}, {"42"});
        QTRY_VERIFY(manager.supported());
        QVERIFY(!manager.frameFor("42")->hasFrame());
    }
    void uncapturedHiddenWindowAndSnapshotDeadline()
    {
        CaptureServer server;
        server.stalled = true;
        WindowPreviewManager manager;
        manager.open(server.path);
        manager.setWindows({"42", "43"}, {"43"});
        QTRY_VERIFY(manager.supported());
        QTRY_VERIFY(server.captures.value("42") > 0);
        QVERIFY(!manager.frameFor("43")->hasFrame());
        QCOMPARE(server.captures.value("43"), 0);
        QSignalSpy completed(&manager, &WindowPreviewManager::snapshotFinished);
        QElapsedTimer elapsed;
        elapsed.start();
        manager.requestSnapshot("42");
        QTRY_COMPARE_WITH_TIMEOUT(completed.size(), 1, 600);
        QVERIFY(elapsed.elapsed() < 600);
        QCOMPARE(completed.at(0).at(0).toString(), QString("42"));
        QTRY_COMPARE(server.sessions(), 0);
        QPointer<WindowPreviewFrame> old = manager.frameFor("42");
        manager.close(); // The same boundary used by lock/suspend.
        QVERIFY(!old || !old->hasFrame());
        QVERIFY(!manager.frameFor("42"));
        QTest::qWait(300);
        QCOMPARE(completed.size(), 1);
    }
};
QTEST_GUILESS_MAIN(WindowPreviewProtocolTest)
#include "window_preview_protocol_test.moc"
