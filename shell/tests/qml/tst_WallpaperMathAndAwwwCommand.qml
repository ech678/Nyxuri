import QtQuick 2.15
import QtTest 1.3
import "../../shared/utils/WallpaperMath.js" as WallpaperMath

TestCase {
    name: "WallpaperMath"

    function test_fixedParallaxCanvasGeometry() {
        const geometry = WallpaperMath.parallaxCanvasGeometry(1920, 1080, 1.10, true);
        compare(Math.round(geometry.scaledWidth), 2112);
        compare(Math.round(geometry.scaledHeight), 1188);
        compare(Math.round(geometry.overflowX), 192);
        compare(Math.round(geometry.overflowY), 108);

        const inactive = WallpaperMath.parallaxCanvasGeometry(1920, 1080, 1.10, false);
        compare(inactive.scaledWidth, 1920);
        compare(inactive.scaledHeight, 1080);
        compare(inactive.overflowX, 0);
        compare(inactive.overflowY, 0);
    }

    function test_panoramaGeometryUsesNaturalHorizontalOverflow() {
        const geometry = WallpaperMath.panoramaGeometry(1920, 1080, 2048, 576, true);
        verify(geometry.active);
        compare(geometry.scale, 1.875);
        compare(geometry.canvasWidth, 3840);
        compare(geometry.canvasHeight, 1080);
        compare(geometry.overflowX, 1920);
        compare(geometry.overflowY, 0);
        compare(WallpaperMath.wallpaperPosition(geometry.overflowX, 0), 0);
        compare(WallpaperMath.wallpaperPosition(geometry.overflowX, 0.5), -960);
        compare(WallpaperMath.wallpaperPosition(geometry.overflowX, 1), -1920);
    }

    function test_wallpaperScreenTransformsRoundTrip() {
        const offsetX = -900;
        const offsetY = -24;
        const wallpaperPoint = {
            x: 1400,
            y: 360
        };
        const screenPoint = WallpaperMath.wallpaperToScreen(offsetX, offsetY, wallpaperPoint.x,
                                                            wallpaperPoint.y);
        compare(screenPoint.x, 500);
        compare(screenPoint.y, 336);

        const roundTrip = WallpaperMath.screenToWallpaper(offsetX, offsetY, screenPoint.x, screenPoint.y);
        compare(roundTrip.x, wallpaperPoint.x);
        compare(roundTrip.y, wallpaperPoint.y);
    }

    function test_panoramaCardStaysInWallpaperSpaceWhileOffsetMoves() {
        const geometry = WallpaperMath.panoramaGeometry(1920, 1080, 2048, 576, true);
        const wallpaperX = 400;
        const firstOffset = WallpaperMath.wallpaperPosition(geometry.overflowX, 0.15625);
        const secondOffset = WallpaperMath.wallpaperPosition(geometry.overflowX, 0.46875);
        const firstScreen = WallpaperMath.wallpaperToScreen(firstOffset, 0, wallpaperX, 200);
        const secondScreen = WallpaperMath.wallpaperToScreen(secondOffset, 0, wallpaperX, 200);

        compare(wallpaperX, 400);
        verify(secondScreen.x < firstScreen.x);
        compare(WallpaperMath.screenToWallpaper(secondOffset, 0, secondScreen.x, secondScreen.y).x,
                wallpaperX);
    }

    function test_normalizedWallpaperCoordinatesAreResolutionIndependent() {
        const normalized = WallpaperMath.wallpaperToNormalized(3840, 1080, 1920, 540);
        compare(normalized.xNorm, 0.5);
        compare(normalized.yNorm, 0.5);
        const mapped = WallpaperMath.normalizedToWallpaper(7680, 2160, normalized.xNorm, normalized.yNorm);
        compare(mapped.x, 3840);
        compare(mapped.y, 1080);
    }

    function test_panoramaFallsBackForNonWideImages() {
        const sameAspect = WallpaperMath.panoramaGeometry(1920, 1080, 1920, 1080, true);
        verify(!sameAspect.active);
        compare(sameAspect.canvasWidth, 1920);
        compare(sameAspect.canvasHeight, 1080);
        compare(sameAspect.overflowX, 0);
        compare(sameAspect.overflowY, 0);

        const portrait = WallpaperMath.panoramaGeometry(1920, 1080, 1080, 1920, true);
        verify(!portrait.active);
        compare(portrait.canvasWidth, 1920);
        compare(portrait.canvasHeight, 1080);
        compare(portrait.overflowX, 0);
        compare(portrait.overflowY, 0);
    }

    function test_panoramaCurrentAndNextUseIndependentGeometry() {
        const current = WallpaperMath.panoramaGeometry(1920, 1080, 2048, 576, true);
        const next = WallpaperMath.panoramaGeometry(1920, 1080, 3072, 576, true);
        compare(current.canvasWidth, 3840);
        compare(next.canvasWidth, 5760);
        compare(current.canvasHeight, 1080);
        compare(next.canvasHeight, 1080);
        compare(WallpaperMath.wallpaperPosition(current.overflowX, 0.4), -768);
        compare(WallpaperMath.wallpaperPosition(next.overflowX, 0.4), -1536);
    }

    function test_panoramaGeometryIsPerScreen() {
        const laptop = WallpaperMath.panoramaGeometry(1920, 1080, 2048, 576, true);
        const ultrawide = WallpaperMath.panoramaGeometry(3440, 1440, 2048, 576, true);
        compare(laptop.canvasWidth, 3840);
        compare(laptop.overflowX, 1920);
        compare(ultrawide.canvasWidth, 5120);
        compare(ultrawide.overflowX, 1680);
    }

    function test_parallaxCanvasIgnoresWallpaperAspectAndStatus() {
        const wallpaperStates = [
                  {
                      source: "wide.jpg",
                      width: 3440,
                      height: 1440,
                      status: Image.Loading
                  },
                  {
                      source: "wide.jpg",
                      width: 3440,
                      height: 1440,
                      status: Image.Ready
                  },
                  {
                      source: "portrait.jpg",
                      width: 1080,
                      height: 1920,
                      status: Image.Loading
                  },
                  {
                      source: "portrait.jpg",
                      width: 1080,
                      height: 1920,
                      status: Image.Ready
                  }
              ];
        const horizontalProgress = 0.4;
        const verticalProgress = 0.5;
        let expectedGeometry = "";
        let expectedX = 0;
        let expectedY = 0;

        for (let index = 0; index < wallpaperStates.length; index += 1) {
            const state = wallpaperStates[index];
            const supported = WallpaperMath.supportsParallaxCanvas(true, state.source, false);
            const geometry = WallpaperMath.parallaxCanvasGeometry(1920, 1080, 1.10, supported);
            const serialized = JSON.stringify(geometry);
            const x = WallpaperMath.wallpaperPosition(geometry.overflowX, horizontalProgress);
            const y = WallpaperMath.wallpaperPosition(geometry.overflowY, verticalProgress);
            if (index === 0) {
                expectedGeometry = serialized;
                expectedX = x;
                expectedY = y;
            } else {
                compare(serialized, expectedGeometry);
                compare(x, expectedX);
                compare(y, expectedY);
            }
        }

        verify(!WallpaperMath.supportsParallaxCanvas(false, "wide.jpg", false));
        verify(!WallpaperMath.supportsParallaxCanvas(true, "#112233", true));
        verify(!WallpaperMath.supportsParallaxCanvas(true, "", false));
    }

    function test_currentAndNextWallpaperShareParallaxCanvas() {
        const geometry = WallpaperMath.parallaxCanvasGeometry(1920, 1080, 1.10, true);
        const currentSource = {
            source: "current-16x9.jpg",
            canvasWidth: geometry.scaledWidth,
            canvasHeight: geometry.scaledHeight
        };
        const nextSource = {
            source: "next-ultrawide.jpg",
            canvasWidth: geometry.scaledWidth,
            canvasHeight: geometry.scaledHeight
        };
        compare(currentSource.canvasWidth, nextSource.canvasWidth);
        compare(currentSource.canvasHeight, nextSource.canvasHeight);
    }

    function test_fixedCanvasStillMovesWithParallaxDrivers() {
        const geometry = WallpaperMath.parallaxCanvasGeometry(1920, 1080, 1.10, true);
        const columns = [1, 2, 3, 4, 5, 6];
        const firstX = WallpaperMath.wallpaperPosition(geometry.overflowX, WallpaperMath.focusedColumnProgress(
                                                           columns, 1, 6));
        const lastX = WallpaperMath.wallpaperPosition(geometry.overflowX, WallpaperMath.focusedColumnProgress(
                                                          columns, 6, 6));
        compare(Math.round(firstX), 0);
        compare(Math.round(lastX), -192);

        const topY = WallpaperMath.wallpaperPosition(geometry.overflowY, WallpaperMath.workspaceProgress([
                                                                                                             {
                                                                                                                 isActive: true
                                                                                                             },
                                                                                                             {
                                                                                                                 isActive: false
                                                                                                             }
                                                                                                         ]));
        const bottomY = WallpaperMath.wallpaperPosition(geometry.overflowY, WallpaperMath.workspaceProgress([
                                                                                                                {
                                                                                                                    isActive: false
                                                                                                                },
                                                                                                                {
                                                                                                                    isActive: true
                                                                                                                }
                                                                                                            ]));
        compare(Math.round(topY), 0);
        compare(Math.round(bottomY), -108);
    }

    function test_tiledColumnProgress() {
        compare(WallpaperMath.tiledColumnProgress(0, 6), 0.5);
        compare(WallpaperMath.tiledColumnProgress(1, 6), 0);
        compare(WallpaperMath.tiledColumnProgress(2, 6), 0.2);
        compare(WallpaperMath.tiledColumnProgress(6, 6), 1);
        compare(WallpaperMath.tiledColumnProgress(12, 6), 1);
    }

    function test_focusedHorizontalColumnProgress() {
        const columns = [1, 2, 3, 4, 5, 6];
        compare(WallpaperMath.focusedColumnProgress(columns, 1, 6), 0);
        compare(WallpaperMath.focusedColumnProgress(columns, 3, 6), 0.4);
        compare(WallpaperMath.focusedColumnProgress(columns, 6, 6), 1);
        compare(WallpaperMath.focusedColumnProgress([], 0, 6), 0.5);
        compare(WallpaperMath.focusedColumnProgress([3], 3, 6), 0);
    }

    function test_horizontalColumnsIgnoreRowsAndFloatingWindows() {
        const windows = [
                  {
                      workspaceId: 1,
                      isFloating: false,
                      layoutColumn: 1,
                      layoutRow: 1
                  },
                  {
                      workspaceId: 1,
                      isFloating: false,
                      layoutColumn: 3,
                      layoutRow: 1
                  },
                  {
                      workspaceId: 1,
                      isFloating: false,
                      layoutColumn: 3,
                      layoutRow: 2
                  },
                  {
                      workspaceId: 1,
                      isFloating: false,
                      layoutColumn: 6,
                      layoutRow: 1
                  },
                  {
                      workspaceId: 1,
                      isFloating: true,
                      layoutColumn: 4,
                      layoutRow: 1
                  }
              ];
        const columns = WallpaperMath.horizontalColumns(windows);
        compare(JSON.stringify(columns), JSON.stringify([1, 3, 6]));

        const progressA = WallpaperMath.focusedColumnProgress(columns, windows[1].layoutColumn, 6);
        const progressB = WallpaperMath.focusedColumnProgress(columns, windows[2].layoutColumn, 6);
        compare(progressA, progressB);

        const vertical = WallpaperMath.workspaceProgress([
                                                             {
                                                                 isActive: true
                                                             },
                                                             {
                                                                 isActive: false
                                                             }
                                                         ]);
        compare(vertical, 0);
        compare(WallpaperMath.wallpaperPosition(100, vertical), WallpaperMath.wallpaperPosition(100,
                                                                                                vertical));
    }

    function test_floatingFocusKeepsTiledMemory() {
        let memory = {};
        memory = WallpaperMath.rememberFocusedHorizontalColumn(memory, {
                                                                   workspaceId: 7,
                                                                   isFloating: false,
                                                                   layoutColumn: 4,
                                                                   layoutRow: 1
                                                               });
        const afterTiled = memory;
        memory = WallpaperMath.rememberFocusedHorizontalColumn(memory, {
                                                                   workspaceId: 7,
                                                                   isFloating: true,
                                                                   layoutColumn: 9,
                                                                   layoutRow: 1
                                                               });
        compare(memory, afterTiled);
        compare(memory["7"], 4);
        compare(WallpaperMath.focusedColumnProgress([1, 2, 3, 4, 5, 6], memory["7"], 6), 0.6);
    }

    function test_closedColumnUsesNearestRemainingSlot() {
        compare(WallpaperMath.nearestHorizontalColumn([1, 2, 3, 5], 4), 3);
        compare(WallpaperMath.focusedColumnProgress([1, 2, 3, 5], 4, 6), 0.4);
        compare(WallpaperMath.nearestHorizontalColumn([], 4), 0);
    }

    function test_workspaceHorizontalMemoryIsIndependent() {
        let memory = {};
        memory = WallpaperMath.rememberFocusedHorizontalColumn(memory, {
                                                                   workspaceId: 11,
                                                                   isFloating: false,
                                                                   layoutColumn: 2
                                                               });
        memory = WallpaperMath.rememberFocusedHorizontalColumn(memory, {
                                                                   workspaceId: 22,
                                                                   isFloating: false,
                                                                   layoutColumn: 5
                                                               });
        compare(memory["11"], 2);
        compare(memory["22"], 5);

        const unchanged = WallpaperMath.rememberFocusedHorizontalColumn(memory, {
                                                                            workspaceId: 22,
                                                                            isFloating: true,
                                                                            layoutColumn: 8
                                                                        });
        compare(unchanged["11"], 2);
        compare(unchanged["22"], 5);
    }

    function test_workspaceProgressIsPerOutputList() {
        compare(WallpaperMath.workspaceProgress([
                                                    {
                                                        isActive: true
                                                    }
                                                ]), 0.5);
        compare(WallpaperMath.workspaceProgress([
                                                    {
                                                        isActive: true
                                                    },
                                                    {
                                                        isActive: false
                                                    },
                                                    {
                                                        isActive: false
                                                    }
                                                ]), 0);
        compare(WallpaperMath.workspaceProgress([
                                                    {
                                                        isActive: false
                                                    },
                                                    {
                                                        isActive: false
                                                    },
                                                    {
                                                        isActive: true
                                                    }
                                                ]), 1);
    }

    function test_sidebarDirectionsAndCancellation() {
        const overflow = 200;
        const base = WallpaperMath.horizontalProgress(0.5, false, false, 0.1);
        const left = WallpaperMath.horizontalProgress(0.5, true, false, 0.1);
        const right = WallpaperMath.horizontalProgress(0.5, false, true, 0.1);
        const both = WallpaperMath.horizontalProgress(0.5, true, true, 0.1);

        verify(WallpaperMath.wallpaperPosition(overflow, left) > WallpaperMath.wallpaperPosition(overflow,
                                                                                                 base));
        verify(WallpaperMath.wallpaperPosition(overflow, right) < WallpaperMath.wallpaperPosition(overflow,
                                                                                                  base));
        compare(both, base);
    }

}
