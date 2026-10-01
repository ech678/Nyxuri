#include "niri_workspace_deriver.h"
#include "niri_workspace_model.h"

#include <QtTest>

class NiriWorkspaceDeriverTest : public QObject {
    Q_OBJECT

  private:
    static NiriWindow window(quint64 id, bool floating, int column, quint64 workspaceId = 1)
    {
        NiriWindow result;
        result.id = id;
        result.workspaceId = workspaceId;
        result.isFloating = floating;
        result.layoutColumn = column;
        return result;
    }

    static NiriWorkspace derive(const QList<NiriWindow> &windows)
    {
        QList<NiriWorkspace> workspaces(1);
        workspaces[0].id = 1;
        NiriWorkspaceDeriver::recomputeWindowCounts(workspaces, windows);
        return workspaces.first();
    }

  private slots:
    void oneTiledTwoFloating()
    {
        const NiriWorkspace workspace = derive({
            window(1, false, 1),
            window(2, true, 999999),
            window(3, true, 999999),
        });

        QCOMPARE(workspace.windowCount, 3);
        QCOMPARE(workspace.tiledWindowCount, 1);
        QCOMPARE(workspace.tiledColumnCount, 1);
    }

    void sharedAndDistinctColumnsIgnoreFloating()
    {
        const NiriWorkspace workspace = derive({
            window(1, false, 1),
            window(2, false, 1),
            window(3, false, 2),
            window(4, true, 999999),
            window(5, true, 999999),
        });

        QCOMPARE(workspace.windowCount, 5);
        QCOMPARE(workspace.tiledWindowCount, 3);
        QCOMPARE(workspace.tiledColumnCount, 2);
    }

    void floatingLifecycleDoesNotChangeTiledColumns()
    {
        QList<NiriWindow> windows{
            window(1, false, 1),
            window(2, false, 2),
        };
        QCOMPARE(derive(windows).tiledColumnCount, 2);
        QCOMPARE(derive(windows).tiledWindowCount, 2);

        windows.append(window(3, true, 999999));
        QCOMPARE(derive(windows).tiledColumnCount, 2);
        QCOMPARE(derive(windows).tiledWindowCount, 2);

        windows[2].layoutColumn = 4;
        QCOMPARE(derive(windows).tiledColumnCount, 2);
        QCOMPARE(derive(windows).tiledWindowCount, 2);

        windows.removeLast();
        QCOMPARE(derive(windows).tiledColumnCount, 2);
        QCOMPARE(derive(windows).tiledWindowCount, 2);
    }

    void movingFloatingWindowBetweenWorkspacesDoesNotAffectTiledCounts()
    {
        QList<NiriWorkspace> workspaces(2);
        workspaces[0].id = 1;
        workspaces[1].id = 2;
        QList<NiriWindow> windows{
            window(1, false, 1, 1),
            window(2, false, 2, 1),
            window(3, true, 999999, 1),
            window(4, false, 1, 2),
        };

        NiriWorkspaceDeriver::recomputeWindowCounts(workspaces, windows);
        QCOMPARE(workspaces[0].windowCount, 3);
        QCOMPARE(workspaces[0].tiledWindowCount, 2);
        QCOMPARE(workspaces[0].tiledColumnCount, 2);
        QCOMPARE(workspaces[1].windowCount, 1);
        QCOMPARE(workspaces[1].tiledWindowCount, 1);
        QCOMPARE(workspaces[1].tiledColumnCount, 1);

        windows[2].workspaceId = 2;
        NiriWorkspaceDeriver::recomputeWindowCounts(workspaces, windows);
        QCOMPARE(workspaces[0].windowCount, 2);
        QCOMPARE(workspaces[0].tiledWindowCount, 2);
        QCOMPARE(workspaces[0].tiledColumnCount, 2);
        QCOMPARE(workspaces[1].windowCount, 2);
        QCOMPARE(workspaces[1].tiledWindowCount, 1);
        QCOMPARE(workspaces[1].tiledColumnCount, 1);
    }

    void tiledColumnTopologyTracksConsumeAndExpel()
    {
        QList<NiriWindow> windows{
            window(1, false, 1),
            window(2, false, 2),
        };
        QCOMPARE(derive(windows).tiledColumnCount, 2);

        windows.append(window(3, false, 2));
        QCOMPARE(derive(windows).tiledColumnCount, 2);

        windows[1].layoutColumn = 1;
        windows[2].layoutColumn = 1;
        QCOMPARE(derive(windows).tiledColumnCount, 1);

        windows[2].layoutColumn = 3;
        QCOMPARE(derive(windows).tiledColumnCount, 2);
    }

    void nonPositiveColumnsAreNotCounted()
    {
        const NiriWorkspace workspace = derive({
            window(1, false, 0),
            window(2, false, -1),
            window(3, false, 999999),
        });

        QCOMPARE(workspace.windowCount, 3);
        QCOMPARE(workspace.tiledWindowCount, 3);
        QCOMPARE(workspace.tiledColumnCount, 1);
    }

    void modelExportsTiledRolesAndMaps()
    {
        NiriWorkspace workspace;
        workspace.id = 7;
        workspace.output = QStringLiteral("DP-1");
        workspace.windowCount = 5;
        workspace.tiledWindowCount = 3;
        workspace.tiledColumnCount = 2;

        NiriWorkspaceModel model;
        model.setWorkspaces({workspace});

        QCOMPARE(model.roleNames().value(NiriWorkspaceModel::TiledWindowCountRole),
                 QByteArray("tiledWindowCount"));
        QCOMPARE(model.roleNames().value(NiriWorkspaceModel::TiledColumnCountRole),
                 QByteArray("tiledColumnCount"));
        QCOMPARE(model.data(model.index(0), NiriWorkspaceModel::TiledWindowCountRole).toInt(), 3);
        QCOMPARE(model.data(model.index(0), NiriWorkspaceModel::TiledColumnCountRole).toInt(), 2);

        const QVariantList outputWorkspaces = model.workspacesForOutput(QStringLiteral("DP-1"));
        QCOMPARE(outputWorkspaces.size(), 1);
        const QVariantMap map = outputWorkspaces.first().toMap();
        QCOMPARE(map.value(QStringLiteral("windowCount")).toInt(), 5);
        QCOMPARE(map.value(QStringLiteral("tiledWindowCount")).toInt(), 3);
        QCOMPARE(map.value(QStringLiteral("tiledColumnCount")).toInt(), 2);
    }
};

QTEST_GUILESS_MAIN(NiriWorkspaceDeriverTest)

#include "niri_workspace_deriver_test.moc"
