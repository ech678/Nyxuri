#include "window_capture_probe.h"
#include <QCommandLineParser>
#include <QCryptographicHash>
#include <QDir>
#include <QElapsedTimer>
#include <QGuiApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QQmlApplicationEngine>
#include <QSet>
#include <QTimer>
#include <cstdio>

static void report(const QJsonObject &value)
{
    const auto data = QJsonDocument(value).toJson(QJsonDocument::Compact);
    std::fwrite(data.constData(), 1, size_t(data.size()), stdout);
    std::fputc('\n', stdout);
    std::fflush(stdout);
}
int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);
    app.setApplicationName("clavis-window-preview");
    QCommandLineParser parser;
    parser.setApplicationDescription(
        "Standalone SHM ext toplevel capture probe; never starts Clavis services.");
    parser.addHelpOption();
    parser.addOptions({{{"d", "display"}, "Explicit capture Wayland socket.", "socket"},
                       {"list", "List protocol toplevels as JSON and exit."},
                       {"view", "Immediately preview this identifier in the GUI.", "identifier"},
                       {"capture", "Capture this stable ext identifier without a viewer.", "identifier"},
                       {"frames", "Frames per capture cycle.", "count", "10"},
                       {"cycles", "Stop and recreate the session this many times.", "count", "1"},
                       {"alternate", "Alternate capture cycles with this identifier.", "identifier"},
                       {"timeout", "Bounded probe lifetime in milliseconds.", "ms", "15000"},
                       {"save", "Save the final captured frame once (PNG).", "path"},
                       {"fixture", "Show an isolated animated test window (A or B).", "label"},
                       {"static", "Disable fixture animation."}});
    parser.process(app);
    app.setDesktopFileName(parser.isSet("fixture") ? "clavis-window-preview-fixture"
                                                   : "clavis-window-preview");
    bool valid = false;
    const int timeout = parser.value("timeout").toInt(&valid);
    if (!valid || timeout < 100 || timeout > 3600000)
        return 2;
    const int frames = parser.value("frames").toInt(&valid);
    if (!valid || frames < 1 || frames > 100000)
        return 2;
    const int cycles = parser.value("cycles").toInt(&valid);
    if (!valid || cycles < 1 || cycles > 10000)
        return 2;
    QQmlApplicationEngine engine;
    engine.addImportPath(QStringLiteral(CLAVIS_CAPTURE_IMPORT_PATH));
    if (parser.isSet("fixture")) {
        engine.setInitialProperties(
            {{"label", parser.value("fixture")}, {"animate", !parser.isSet("static")}});
        engine.load(QUrl("qrc:/probe/Fixture.qml"));
        if (engine.rootObjects().isEmpty())
            return 2;
        QTimer::singleShot(timeout, &app, &QCoreApplication::quit);
        return app.exec();
    }
    if (!parser.isSet("display")) {
        parser.showHelp(2);
    }
    WindowCaptureProbe capture;
    const bool batch = parser.isSet("list") || parser.isSet("capture");
    bool started = false, finishing = false;
    int completed = 0, total = 0;
    QImage last;
    QSet<QByteArray> hashes;
    QElapsedTimer elapsed;
    elapsed.start();
    const auto descriptors = [] {
        return QDir("/proc/self/fd").entryList(QDir::AllEntries | QDir::NoDotAndDotDot).size();
    };
    int baselineFds = 0;
    auto finish = [&](int result, const QString &reason) {
        if (finishing)
            return;
        finishing = true;
        if (parser.isSet("save") && !last.isNull() && !last.save(parser.value("save")))
            result = 2;
        capture.stop();
        report({{"event", "summary"},
                {"result", result},
                {"reason", reason},
                {"frames", total},
                {"distinctFrames", hashes.size()},
                {"cycles", completed},
                {"elapsedMs", elapsed.elapsed()},
                {"baselineFds", baselineFds},
                {"finalFds", descriptors()},
                {"activeSessions", capture.active() ? 1 : 0}});
        capture.close();
        app.exit(result);
    };
    QObject::connect(&capture, &WindowCaptureProbe::changed, &app, [&] {
        if (finishing)
            return;
        if (!batch) {
            if (capture.ready() && capture.supported() && !started && parser.isSet("view")) {
                started = true;
                QTimer::singleShot(0, &app, [&] { capture.start(parser.value("view")); });
            }
            return;
        }
        if (!capture.error().isEmpty()) {
            QTimer::singleShot(0, &app, [&] { finish(2, capture.error()); });
            return;
        }
        if (capture.ready() && !started) {
            started = true;
            QTimer::singleShot(0, &app, [&] {
                if (parser.isSet("list")) {
                    report({{"event", "windows"},
                            {"supported", capture.supported()},
                            {"windows", QJsonArray::fromVariantList(capture.windows())}});
                    finish(0, "listed");
                } else {
                    baselineFds = descriptors();
                    capture.start(parser.value("capture"));
                }
            });
        }
    });
    QObject::connect(&capture, &WindowCaptureProbe::imageChanged, &app, [&] {
        if (!batch || finishing || capture.image().isNull())
            return;
        last = capture.image();
        ++total;
        const auto hash =
            QCryptographicHash::hash(
                QByteArrayView(reinterpret_cast<const char *>(last.constBits()), last.sizeInBytes()),
                QCryptographicHash::Sha256)
                .toHex();
        hashes.insert(hash);
        report({{"event", "frame"},
                {"identifier", capture.identifier()},
                {"cycle", completed},
                {"frame", capture.frameCount()},
                {"firstFrameMs", capture.firstFrameMs()},
                {"elapsedMs", elapsed.elapsed()},
                {"sample", last.pixelColor(last.width() / 2, last.height() / 4).name()},
                {"width", last.width()},
                {"height", last.height()},
                {"sha256", QString::fromLatin1(hash)}});
        if (capture.frameCount() >= frames) {
            ++completed;
            capture.stop();
            QTimer::singleShot(0, &app, [&] {
                if (completed >= cycles)
                    finish(0, "completed");
                else
                    capture.start(parser.isSet("alternate") && completed % 2 ? parser.value("alternate")
                                                                             : parser.value("capture"));
            });
        }
    });
    if (!batch) {
        engine.setInitialProperties({{"capture", QVariant::fromValue(&capture)}});
        engine.load(QUrl("qrc:/probe/Preview.qml"));
        if (engine.rootObjects().isEmpty())
            return 2;
    }
    QTimer::singleShot(timeout, &app, [&] {
        if (batch)
            finish(3, "timeout-no-new-frame");
        else
            app.quit();
    });
    QTimer::singleShot(0, &app, [&] { capture.open(parser.value("display")); });
    return app.exec();
}
