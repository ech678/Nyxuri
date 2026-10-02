#pragma once

#include "niri_types.h"

#include <QList>

namespace NiriWorkspaceDeriver {

void recomputeWindowCounts(QList<NiriWorkspace> &workspaces, const QList<NiriWindow> &windows);

}
