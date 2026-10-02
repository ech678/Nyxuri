#include "window_preview_cache.h"
#include <QSignalSpy>
#include <QtTest>

class WindowPreviewCacheTest : public QObject {
    Q_OBJECT
  private slots:
    void ownsBoundedImageAfterSourceDisappears()
    {
        WindowPreviewCache cache;
        cache.reset(7);
        QImage source(1024, 768, QImage::Format_ARGB32_Premultiplied);
        source.fill(Qt::red);
        QVERIFY(cache.store(7, "42", source, source.size()));
        auto *frame = cache.frameFor("42");
        source.fill(Qt::blue);
        source = {};
        QVERIFY(frame->hasFrame());
        QCOMPARE(frame->image().size(), QSize(512, 384));
        QCOMPARE(frame->sourceSize(), QSize(1024, 768));
        QCOMPARE(frame->image().pixelColor(1, 1), QColor(Qt::red));
        QVERIFY(cache.bytesUsed() <= 512 * 512 * 4);
        QVERIFY(!cache.store(7, "42", {}, {}));
        QCOMPARE(frame->image().pixelColor(1, 1), QColor(Qt::red));
    }
    void generationAndClosurePreventReusedIdentity()
    {
        WindowPreviewCache cache;
        cache.reset(1);
        QImage source(16, 16, QImage::Format_RGB32);
        source.fill(Qt::red);
        QVERIFY(cache.store(1, "42", source, source.size()));
        auto *old = cache.frameFor("42");
        QSignalSpy invalidated(old, &WindowPreviewFrame::changed);
        cache.reset(2);
        QVERIFY(!old->hasFrame());
        QCOMPARE(invalidated.size(), 1);
        QVERIFY(!cache.store(1, "42", source, source.size()));
        QVERIFY(!cache.hasFrame("42"));
        source.fill(Qt::blue);
        QVERIFY(cache.store(2, "42", source, source.size()));
        QCOMPARE(cache.frameFor("42")->image().pixelColor(0, 0), QColor(Qt::blue));
        cache.retain({"43"});
        QVERIFY(!cache.hasFrame("42"));
        QCOMPARE(cache.bytesUsed(), 0);
    }
    void budgetEvictsLeastRecentlyUsedAndRevocationClears()
    {
        const qint64 size = 64 * 64 * 4;
        WindowPreviewCache cache(nullptr, size * 2);
        QImage image(64, 64, QImage::Format_ARGB32_Premultiplied);
        image.fill(Qt::green);
        QVERIFY(cache.store(0, "1", image, image.size()));
        QVERIFY(cache.store(0, "2", image, image.size()));
        auto *evicted = cache.frameFor("2");
        cache.frameFor("1");
        QVERIFY(cache.store(0, "3", image, image.size()));
        QVERIFY(!evicted->hasFrame());
        QVERIFY(cache.hasFrame("1"));
        QVERIFY(cache.hasFrame("3"));
        QCOMPARE(cache.bytesUsed(), size * 2);
        cache.invalidate("1");
        QVERIFY(!cache.hasFrame("1"));
        QCOMPARE(cache.frameFor("1")->sourceSize(), QSize());
        QCOMPARE(cache.bytesUsed(), size);
    }
};
QTEST_GUILESS_MAIN(WindowPreviewCacheTest)
#include "window_preview_cache_test.moc"
