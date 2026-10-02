#include "window_capture_probe.h"
#include "ext-foreign-toplevel-list-v1-client-protocol.h"
#include "ext-image-capture-source-v1-client-protocol.h"
#include "ext-image-copy-capture-v1-client-protocol.h"
#include <QElapsedTimer>
#include <QSocketNotifier>
#include <QTimer>
#include <cerrno>
#include <cstring>
#include <limits>
#include <map>
#include <sys/mman.h>
#include <unistd.h>
#include <wayland-client.h>

struct WindowCaptureProbe::Private {
    WindowCaptureProbe *q;
    wl_display *display = nullptr;
    wl_registry *registry = nullptr;
    wl_callback *sync = nullptr;
    wl_shm *shm = nullptr;
    ext_foreign_toplevel_list_v1 *list = nullptr;
    ext_foreign_toplevel_image_capture_source_manager_v1 *sources = nullptr;
    ext_image_copy_capture_manager_v1 *manager = nullptr;
    ext_image_capture_source_v1 *source = nullptr;
    ext_image_copy_capture_session_v1 *session = nullptr;
    ext_image_copy_capture_frame_v1 *frame = nullptr;
    QSocketNotifier *reader = nullptr;
    QSocketNotifier *writer = nullptr;
    QTimer handshake;
    QTimer next;
    QElapsedTimer elapsed;
    unsigned connectionGeneration = 0;
    bool ready = false;
    bool supported = false;
    QString error;
    QString identifier;
    int frames = 0;
    qint64 firstMs = -1;
    QImage image;
    QSize sourceSize;
    int maximumDimension = 0;
    int frameInterval = 33;
    struct Window {
        Private *owner;
        ext_foreign_toplevel_handle_v1 *handle;
        QString id, title, app;
        QVariantMap committed;
    };
    std::map<ext_foreign_toplevel_handle_v1 *, std::unique_ptr<Window>> windows;
    std::map<uint32_t, QString> globals;
    struct Constraints {
        uint32_t width = 0, height = 0;
        bool argb = false, xrgb = false;
    } pending, current, allocated;
    bool batch = false;
    bool constrained = false;
    wl_buffer *buffer = nullptr;
    void *pixels = MAP_FAILED;
    size_t bytes = 0;
    int stride = 0;
    int retries = 0;
    uint32_t transform = 0;
    QImage::Format imageFormat = QImage::Format_Invalid;

    explicit Private(WindowCaptureProbe *owner) : q(owner)
    {
        next.setSingleShot(true);
        QObject::connect(&next, &QTimer::timeout, q, [this] { capture(); });
        handshake.setSingleShot(true);
        QObject::connect(&handshake, &QTimer::timeout, q, [this] {
            fail("registry-timeout");
            disconnect();
        });
    }
    void fail(const QString &reason)
    {
        error = reason;
        stop();
    }
    void flush()
    {
        if (!display)
            return;
        const int result = wl_display_flush(display);
        if (result < 0 && errno != EAGAIN) {
            fail("wayland-flush-failed");
            disconnect();
        } else if (writer) {
            writer->setEnabled(result < 0);
        }
    }
    void freeBuffer()
    {
        if (buffer)
            wl_buffer_destroy(buffer);
        buffer = nullptr;
        if (pixels != MAP_FAILED)
            munmap(pixels, bytes);
        pixels = MAP_FAILED;
        bytes = 0;
        allocated = {};
    }
    void stop()
    {
        next.stop();
        if (frame)
            ext_image_copy_capture_frame_v1_destroy(frame);
        frame = nullptr;
        if (session)
            ext_image_copy_capture_session_v1_destroy(session);
        session = nullptr;
        if (source)
            ext_image_capture_source_v1_destroy(source);
        source = nullptr;
        freeBuffer();
        constrained = false;
        batch = false;
        pending = current = {};
        image = {};
        sourceSize = {};
        emit q->imageChanged();
        emit q->changed();
    }
    void disconnectLater()
    {
        if (reader)
            reader->setEnabled(false);
        if (writer)
            writer->setEnabled(false);
        const auto generation = connectionGeneration;
        QTimer::singleShot(0, q, [this, generation] {
            if (generation == connectionGeneration)
                disconnect();
        });
    }
    void disconnect()
    {
        ++connectionGeneration;
        handshake.stop();
        stop();
        delete reader;
        delete writer;
        reader = writer = nullptr;
        if (sync)
            wl_callback_destroy(sync);
        sync = nullptr;
        for (auto &entry : windows)
            ext_foreign_toplevel_handle_v1_destroy(entry.first);
        windows.clear();
        // Disconnecting owns the whole private connection; no other clients or
        // Qt's Wayland connection share these proxies.
        if (list)
            wl_proxy_destroy(reinterpret_cast<wl_proxy *>(list));
        if (sources)
            ext_foreign_toplevel_image_capture_source_manager_v1_destroy(sources);
        if (manager)
            ext_image_copy_capture_manager_v1_destroy(manager);
        if (shm)
            wl_shm_destroy(shm);
        if (registry)
            wl_registry_destroy(registry);
        if (display)
            wl_display_disconnect(display);
        display = nullptr;
        registry = nullptr;
        list = nullptr;
        sources = nullptr;
        manager = nullptr;
        shm = nullptr;
        globals.clear();
        ready = supported = false;
        emit q->windowsChanged();
        emit q->changed();
    }
    void beginBatch()
    {
        if (!batch) {
            pending = {};
            batch = true;
        }
    }
    bool allocate()
    {
        if (buffer && allocated.width == current.width && allocated.height == current.height &&
            imageFormat == (current.argb ? QImage::Format_ARGB32_Premultiplied : QImage::Format_RGB32))
            return true;
        freeBuffer();
        const quint64 length = quint64(current.width) * current.height * 4;
        if (!current.width || !current.height || current.width > 16384 || current.height > 16384 ||
            length > 256 * 1024 * 1024 || (!current.argb && !current.xrgb)) {
            fail("unsupported-shm-constraints");
            return false;
        }
        const int fd = memfd_create("clavis-window-preview", MFD_CLOEXEC);
        if (fd < 0) {
            fail("shm-allocation-failed");
            return false;
        }
        if (ftruncate(fd, off_t(length)) < 0) {
            ::close(fd);
            fail("shm-allocation-failed");
            return false;
        }
        pixels = mmap(nullptr, size_t(length), PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        if (pixels == MAP_FAILED) {
            ::close(fd);
            fail("shm-map-failed");
            return false;
        }
        bytes = size_t(length);
        stride = int(current.width * 4);
        auto *pool = wl_shm_create_pool(shm, fd, int(length));
        buffer = wl_shm_pool_create_buffer(pool, 0, int(current.width), int(current.height), stride,
                                           current.argb ? WL_SHM_FORMAT_ARGB8888 : WL_SHM_FORMAT_XRGB8888);
        wl_shm_pool_destroy(pool);
        ::close(fd);
        allocated = current;
        imageFormat = current.argb ? QImage::Format_ARGB32_Premultiplied : QImage::Format_RGB32;
        return true;
    }
    void capture();
    void begin(const QString &id);
    void connectDisplay(const QString &name);
    static const ext_foreign_toplevel_handle_v1_listener windowListener;
    static const ext_foreign_toplevel_list_v1_listener listListener;
    static const wl_registry_listener registryListener;
    static const ext_image_copy_capture_session_v1_listener sessionListener;
    static const ext_image_copy_capture_frame_v1_listener frameListener;
};

const ext_foreign_toplevel_handle_v1_listener WindowCaptureProbe::Private::windowListener = {
    [](void *data, ext_foreign_toplevel_handle_v1 *handle) {
        auto *w = static_cast<Window *>(data);
        auto *d = w->owner;
        if (d->identifier == w->id && d->session)
            d->fail("target-closed");
        ext_foreign_toplevel_handle_v1_destroy(handle);
        d->windows.erase(handle);
        emit d->q->windowsChanged();
    },
    [](void *data, ext_foreign_toplevel_handle_v1 *) {
        auto *w = static_cast<Window *>(data);
        w->committed = {{"identifier", w->id}, {"title", w->title}, {"appId", w->app}};
        emit w->owner->q->windowsChanged();
    },
    [](void *data, ext_foreign_toplevel_handle_v1 *, const char *value) {
        static_cast<Window *>(data)->title = QString::fromUtf8(value);
    },
    [](void *data, ext_foreign_toplevel_handle_v1 *, const char *value) {
        static_cast<Window *>(data)->app = QString::fromUtf8(value);
    },
    [](void *data, ext_foreign_toplevel_handle_v1 *, const char *value) {
        static_cast<Window *>(data)->id = QString::fromUtf8(value);
    }};
const ext_foreign_toplevel_list_v1_listener WindowCaptureProbe::Private::listListener = {
    [](void *data, ext_foreign_toplevel_list_v1 *, ext_foreign_toplevel_handle_v1 *handle) {
        auto *d = static_cast<Private *>(data);
        auto w = std::make_unique<Window>();
        w->owner = d;
        w->handle = handle;
        ext_foreign_toplevel_handle_v1_add_listener(handle, &windowListener, w.get());
        d->windows.emplace(handle, std::move(w));
    },
    [](void *data, ext_foreign_toplevel_list_v1 *) {
        auto *d = static_cast<Private *>(data);
        d->fail("toplevel-list-finished");
        d->disconnectLater();
    }};
const wl_registry_listener WindowCaptureProbe::Private::registryListener = {
    [](void *data, wl_registry *registry, uint32_t name, const char *interface, uint32_t) {
        auto *d = static_cast<Private *>(data);
        const QString type = QString::fromLatin1(interface);
        if (type == "wl_shm")
            d->shm = static_cast<wl_shm *>(wl_registry_bind(registry, name, &wl_shm_interface, 1));
        else if (type == "ext_foreign_toplevel_list_v1") {
            d->list = static_cast<ext_foreign_toplevel_list_v1 *>(
                wl_registry_bind(registry, name, &ext_foreign_toplevel_list_v1_interface, 1));
            ext_foreign_toplevel_list_v1_add_listener(d->list, &listListener, d);
        } else if (type == "ext_foreign_toplevel_image_capture_source_manager_v1")
            d->sources = static_cast<ext_foreign_toplevel_image_capture_source_manager_v1 *>(wl_registry_bind(
                registry, name, &ext_foreign_toplevel_image_capture_source_manager_v1_interface, 1));
        else if (type == "ext_image_copy_capture_manager_v1")
            d->manager = static_cast<ext_image_copy_capture_manager_v1 *>(
                wl_registry_bind(registry, name, &ext_image_copy_capture_manager_v1_interface, 1));
        else
            return;
        d->globals[name] = type;
    },
    [](void *data, wl_registry *, uint32_t name) {
        auto *d = static_cast<Private *>(data);
        if (d->globals.count(name)) {
            d->fail("capture-global-removed");
            d->disconnectLater();
        }
    }};
const ext_image_copy_capture_session_v1_listener WindowCaptureProbe::Private::sessionListener = {
    [](void *data, ext_image_copy_capture_session_v1 *, uint32_t w, uint32_t h) {
        auto *d = static_cast<Private *>(data);
        d->beginBatch();
        d->pending.width = w;
        d->pending.height = h;
    },
    [](void *data, ext_image_copy_capture_session_v1 *, uint32_t format) {
        auto *d = static_cast<Private *>(data);
        d->beginBatch();
        d->pending.argb |= format == WL_SHM_FORMAT_ARGB8888;
        d->pending.xrgb |= format == WL_SHM_FORMAT_XRGB8888;
    },
    [](void *, ext_image_copy_capture_session_v1 *, wl_array *) {},
    [](void *, ext_image_copy_capture_session_v1 *, uint32_t, wl_array *) {},
    [](void *data, ext_image_copy_capture_session_v1 *) {
        auto *d = static_cast<Private *>(data);
        d->current = d->pending;
        d->batch = false;
        d->constrained = true;
        if (!d->frame)
            d->next.start(0);
    },
    [](void *data, ext_image_copy_capture_session_v1 *) {
        static_cast<Private *>(data)->fail("session-stopped");
    }};
const ext_image_copy_capture_frame_v1_listener WindowCaptureProbe::Private::frameListener = {
    [](void *data, ext_image_copy_capture_frame_v1 *, uint32_t transform) {
        static_cast<Private *>(data)->transform = transform;
    },
    [](void *, ext_image_copy_capture_frame_v1 *, int32_t, int32_t, int32_t, int32_t) {},
    [](void *, ext_image_copy_capture_frame_v1 *, uint32_t, uint32_t, uint32_t) {},
    [](void *data, ext_image_copy_capture_frame_v1 *frame) {
        auto *d = static_cast<Private *>(data);
        ext_image_copy_capture_frame_v1_destroy(frame);
        d->frame = nullptr;
        // niri's toplevel capture advertises normal buffers. Refuse other
        // transforms explicitly until that path is validated on real outputs.
        if (d->transform != WL_OUTPUT_TRANSFORM_NORMAL) {
            d->fail("unsupported-buffer-transform");
            return;
        }
        d->sourceSize = QSize(int(d->allocated.width), int(d->allocated.height));
        const QImage raw(static_cast<uchar *>(d->pixels), d->sourceSize.width(), d->sourceSize.height(),
                         d->stride, d->imageFormat);
        d->image = d->maximumDimension > 0 &&
                           (raw.width() > d->maximumDimension || raw.height() > d->maximumDimension)
                       ? raw.scaled(d->maximumDimension, d->maximumDimension, Qt::KeepAspectRatio,
                                    Qt::SmoothTransformation)
                       : raw.copy();
        if (d->image.isNull()) {
            d->fail("image-copy-failed");
            return;
        }
        if (!d->frames)
            d->firstMs = d->elapsed.elapsed();
        ++d->frames;
        d->retries = 0;
        // Schedule before signals: consumers may stop/switch in imageChanged.
        d->next.start(d->frameInterval);
        emit d->q->changed();
        emit d->q->imageChanged();
    },
    [](void *data, ext_image_copy_capture_frame_v1 *frame, uint32_t reason) {
        auto *d = static_cast<Private *>(data);
        ext_image_copy_capture_frame_v1_destroy(frame);
        d->frame = nullptr;
        if (reason == EXT_IMAGE_COPY_CAPTURE_FRAME_V1_FAILURE_REASON_BUFFER_CONSTRAINTS &&
            ++d->retries <= 3) {
            d->freeBuffer();
            d->next.start(d->frameInterval);
        } else
            d->fail(QString("capture-failed:%1").arg(reason));
    }};
void WindowCaptureProbe::Private::capture()
{
    if (!session || frame || !constrained || batch || !allocate())
        return;
    frame = ext_image_copy_capture_session_v1_create_frame(session);
    transform = 0;
    ext_image_copy_capture_frame_v1_add_listener(frame, &frameListener, this);
    ext_image_copy_capture_frame_v1_attach_buffer(frame, buffer);
    ext_image_copy_capture_frame_v1_damage_buffer(frame, 0, 0, int(allocated.width), int(allocated.height));
    ext_image_copy_capture_frame_v1_capture(frame);
    flush();
}
void WindowCaptureProbe::Private::begin(const QString &id)
{
    stop();
    error.clear();
    identifier = id;
    frames = 0;
    firstMs = -1;
    retries = 0;
    if (!supported) {
        fail("capture-protocols-unavailable");
        return;
    }
    Window *target = nullptr;
    for (const auto &entry : windows)
        if (entry.second->id == id)
            target = entry.second.get();
    if (!target) {
        fail("identifier-not-found");
        return;
    }
    elapsed.start();
    source = ext_foreign_toplevel_image_capture_source_manager_v1_create_source(sources, target->handle);
    session = ext_image_copy_capture_manager_v1_create_session(manager, source, 0);
    ext_image_copy_capture_session_v1_add_listener(session, &sessionListener, this);
    flush();
    emit q->changed();
}
void WindowCaptureProbe::Private::connectDisplay(const QString &name)
{
    disconnect();
    error.clear();
    identifier.clear();
    frames = 0;
    firstMs = -1;
    // Require an explicit socket so probes never silently capture the daily session.
    if (name.isEmpty()) {
        fail("display-name-required");
        return;
    }
    display = wl_display_connect(name.toUtf8().constData());
    if (!display) {
        fail("wayland-connect-failed");
        return;
    }
    reader = new QSocketNotifier(wl_display_get_fd(display), QSocketNotifier::Read, q);
    writer = new QSocketNotifier(wl_display_get_fd(display), QSocketNotifier::Write, q);
    writer->setEnabled(false);
    QObject::connect(writer, &QSocketNotifier::activated, q, [this] { flush(); });
    QObject::connect(reader, &QSocketNotifier::activated, q, [this] {
        if (wl_display_dispatch(display) < 0) {
            fail("wayland-disconnected");
            disconnect();
        } else
            flush();
    });
    registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &registryListener, this);
    static const wl_callback_listener complete = {[](void *data, wl_callback *callback, uint32_t) {
        auto *d = static_cast<Private *>(data);
        wl_callback_destroy(callback);
        d->sync = nullptr;
        d->handshake.stop();
        d->ready = true;
        d->supported = d->shm && d->list && d->sources && d->manager;
        if (!d->supported) {
            QStringList missing;
            if (!d->shm)
                missing.append("wl_shm");
            if (!d->list)
                missing.append("ext_foreign_toplevel_list_v1");
            if (!d->sources)
                missing.append("ext_foreign_toplevel_image_capture_source_manager_v1");
            if (!d->manager)
                missing.append("ext_image_copy_capture_manager_v1");
            d->error = "missing-protocols:" + missing.join(',');
        }
        emit d->q->changed();
    }};
    static const wl_callback_listener bound = {[](void *data, wl_callback *callback, uint32_t) {
        auto *d = static_cast<Private *>(data);
        wl_callback_destroy(callback);
        d->sync = wl_display_sync(d->display);
        wl_callback_add_listener(d->sync, &complete, d);
    }};
    sync = wl_display_sync(display);
    wl_callback_add_listener(sync, &bound, this);
    handshake.start(5000);
    flush();
}
WindowCaptureProbe::WindowCaptureProbe(QObject *parent) : QObject(parent), d(std::make_unique<Private>(this))
{}
WindowCaptureProbe::~WindowCaptureProbe() { d->disconnect(); }
QVariantList WindowCaptureProbe::windows() const
{
    QVariantList result;
    for (const auto &entry : d->windows)
        if (!entry.second->committed.isEmpty())
            result.append(entry.second->committed);
    return result;
}
bool WindowCaptureProbe::ready() const { return d->ready; }
bool WindowCaptureProbe::supported() const { return d->supported; }
bool WindowCaptureProbe::active() const { return d->session; }
QString WindowCaptureProbe::error() const { return d->error; }
QString WindowCaptureProbe::identifier() const { return d->identifier; }
int WindowCaptureProbe::frameCount() const { return d->frames; }
qint64 WindowCaptureProbe::firstFrameMs() const { return d->firstMs; }
QSize WindowCaptureProbe::sourceSize() const { return d->sourceSize; }
QImage WindowCaptureProbe::image() const { return d->image; }
void WindowCaptureProbe::open(const QString &displayName) { d->connectDisplay(displayName); }
void WindowCaptureProbe::start(const QString &identifier) { d->begin(identifier); }
void WindowCaptureProbe::stop()
{
    d->stop();
    d->flush();
}
void WindowCaptureProbe::close() { d->disconnect(); }

int WindowCaptureProbe::maximumDimension() const { return d->maximumDimension; }
void WindowCaptureProbe::setMaximumDimension(int value)
{
    const int normalized = value <= 0 ? 0 : qBound(128, value, 2048);
    if (d->maximumDimension == normalized)
        return;
    d->maximumDimension = normalized;
    emit limitsChanged();
}
int WindowCaptureProbe::frameInterval() const { return d->frameInterval; }
void WindowCaptureProbe::setFrameInterval(int value)
{
    const int normalized = qBound(33, value, 1000);
    if (d->frameInterval == normalized)
        return;
    d->frameInterval = normalized;
    emit limitsChanged();
}
