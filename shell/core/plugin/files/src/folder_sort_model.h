#pragma once
#include <QCollator>
#include <QQmlEngine>
#include <QSortFilterProxyModel>
#include <QVariantMap>
class FolderSortModel : public QSortFilterProxyModel {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QString order READ order WRITE setOrder NOTIFY orderChanged)
    Q_PROPERTY(int count READ rowCount NOTIFY countChanged)
  public:
    explicit FolderSortModel(QObject *parent = nullptr);
    QString order() const { return m_order; }
    void setOrder(const QString &value);
    void setSourceModel(QAbstractItemModel *model) override;
    Q_INVOKABLE QVariantMap get(int row) const;
    QHash<int, QByteArray> roleNames() const override;
    QVariant data(const QModelIndex &index, int role) const override;
  signals:
    void orderChanged();
    void countChanged();

  protected:
    bool lessThan(const QModelIndex &left, const QModelIndex &right) const override;

  private:
    QVariantMap metadata(const QModelIndex &source) const;
    mutable QHash<QString, QVariantMap> m_metadata;
    QCollator m_collator;
    QString m_order = "name";
    int m_urlRole = -1;
    bool m_refreshQueued = false;
};
