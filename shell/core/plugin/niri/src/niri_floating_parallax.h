#pragma once

#include "niri_ipc_client.h"
#include "niri_types.h"

#include <QHash>
#include <QObject>
#include <QVariantMap>

// Workspace offsets are targets, not animation samples. Niri owns the animation;
// each window has at most one asynchronous move transaction in progress.
class NiriFloatingParallax : public QObject {
  public:
    static NiriFloatingParallax *shared();
    quint64 acquire();
    void release(quint64 lease);
    bool owns(quint64 lease) const { return lease == m_lease; }
    void setConnected(bool connected, const QString &socketPath);
    void setWindows(const QList<NiriWindow> &windows);
    void setOffsets(const QVariantMap &offsets);

  private:
    explicit NiriFloatingParallax(QObject *parent);
    struct State {
        double appliedOffset = 0;
        double settledTarget = 0;
        double startX = 0;
        double startOffset = 0;
        double sentTarget = 0;
        quint64 serial = 0;
        bool pending = false;
        bool sent = false;
    };

    void reconcile();
    void readPosition(quint64 id, quint64 serial, bool afterMove);
    bool current(quint64 id, quint64 serial, quint64 generation) const;
    double target(quint64 workspaceId) const;
    void finish(quint64 id, bool continueWithLatest);

    NiriIpcClient m_client;
    QList<NiriWindow> m_windows;
    QHash<quint64, State> m_states;
    QHash<quint64, double> m_offsets;
    quint64 m_generation = 0;
    quint64 m_serial = 0;
    quint64 m_lease = 0;
    QString m_socketPath;
    bool m_connected = false;
};
