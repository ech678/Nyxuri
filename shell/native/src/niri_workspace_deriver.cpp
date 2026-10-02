#include "niri_workspace_deriver.h"

#include <QHash>
#include <QSet>

namespace NiriWorkspaceDeriver {

void recomputeWindowCounts(QList<NiriWorkspace> &workspaces, const QList<NiriWindow> &windows)
{
    QHash<quint64, int> windowCounts;
    QHash<quint64, int> tiledWindowCounts;
    QHash<quint64, QSet<int>> tiledColumns;

    for (const NiriWindow &window : windows) {
        windowCounts[window.workspaceId]++;
        if (window.isFloating)
            continue;

        tiledWindowCounts[window.workspaceId]++;
        if (window.layoutColumn > 0)
            tiledColumns[window.workspaceId].insert(window.layoutColumn);
    }

    for (NiriWorkspace &workspace : workspaces) {
        workspace.windowCount = windowCounts.value(workspace.id);
        workspace.tiledWindowCount = tiledWindowCounts.value(workspace.id);
        workspace.tiledColumnCount = tiledColumns.value(workspace.id).size();
    }
}

} // namespace NiriWorkspaceDeriver
