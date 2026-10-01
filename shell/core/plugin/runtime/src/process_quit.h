#pragma once
#include <QObject>
#include <QVariantList>
#include <QtQml/qqmlregistration.h>
#include <vector>

// Keeps process identities stable between a UI confirmation and SIGKILL.
class ProcessQuit : public QObject {
    Q_OBJECT
    QML_ELEMENT
  public:
    explicit ProcessQuit(QObject *parent = nullptr) : QObject(parent) {}
    ~ProcessQuit() override { cancel(); }
    Q_INVOKABLE bool prepare(const QVariantList &pids);
    Q_INVOKABLE bool confirm();
    Q_INVOKABLE void cancel();

  private:
    std::vector<int> m_handles;
};
