#include "folder_sort_model.h"
#include "file_metadata.h"
#include <QDateTime>

FolderSortModel::FolderSortModel(QObject *parent) : QSortFilterProxyModel(parent)
{
    if (m_collator.locale().language() == QLocale::C)
        m_collator.setLocale(QLocale(QLocale::English));
    m_collator.setNumericMode(true);
    m_collator.setCaseSensitivity(Qt::CaseInsensitive);
    connect(this, &QAbstractItemModel::modelReset, this, &FolderSortModel::countChanged);
    connect(this, &QAbstractItemModel::rowsInserted, this, &FolderSortModel::countChanged);
    connect(this, &QAbstractItemModel::rowsRemoved, this, &FolderSortModel::countChanged);
    sort(0);
}
void FolderSortModel::setOrder(const QString &value)
{
    if (m_order == value || !QStringList{"name", "modified", "created", "kind", "size"}.contains(value))
        return;
    m_order = value;
    invalidate();
    emit orderChanged();
}
void FolderSortModel::setSourceModel(QAbstractItemModel *model)
{
    if (sourceModel())
        disconnect(sourceModel(), nullptr, this, nullptr);
    m_metadata.clear();
    m_urlRole = model ? model->roleNames().key("fileUrl", -1) : -1;
    QSortFilterProxyModel::setSourceModel(model);
    if (model) {
        const auto reset = [this] {
            if (m_refreshQueued)
                return;
            m_refreshQueued = true;
            // FolderListModel can replace its list through a removal/insertion
            // batch. Rebuilding a proxy mapping inside that batch duplicates rows.
            QMetaObject::invokeMethod(
                this,
                [this] {
                    m_refreshQueued = false;
                    m_metadata.clear();
                    invalidate();
                },
                Qt::QueuedConnection);
        };
        connect(model, &QAbstractItemModel::modelReset, this, reset);
        connect(model, &QAbstractItemModel::dataChanged, this, reset);
        connect(model, &QAbstractItemModel::rowsRemoved, this, reset);
    }
}
QVariantMap FolderSortModel::metadata(const QModelIndex &source) const
{
    const QUrl url(source.data(m_urlRole).toUrl());
    const auto key = url.toString();
    if (!m_metadata.contains(key))
        m_metadata.insert(key, FileMetadata::read(url));
    return m_metadata.value(key);
}
bool FolderSortModel::lessThan(const QModelIndex &left, const QModelIndex &right) const
{
    const auto a = metadata(left), b = metadata(right);
    if (m_order == "modified" || m_order == "created") {
        const auto x = a.value(m_order).toDateTime(), y = b.value(m_order).toDateTime();
        if (x.isValid() != y.isValid())
            return x.isValid();
        if (x != y)
            return x > y;
    } else if (m_order == "size") {
        if (a.value("size") != b.value("size"))
            return a.value("size").toLongLong() > b.value("size").toLongLong();
    } else if (m_order == "kind") {
        const auto result =
            m_collator.compare(a.value("typeName").toString(), b.value("typeName").toString());
        if (result)
            return result < 0;
    }
    const auto result = m_collator.compare(a.value("name").toString(), b.value("name").toString());
    return result ? result < 0 : a.value("url").toString() < b.value("url").toString();
}
QHash<int, QByteArray> FolderSortModel::roleNames() const { return {{Qt::UserRole, "fileInfo"}}; }
QVariant FolderSortModel::data(const QModelIndex &index, int role) const
{
    return role == Qt::UserRole ? metadata(mapToSource(index)) : QVariant();
}
QVariantMap FolderSortModel::get(int row) const
{
    return row >= 0 && row < rowCount() ? metadata(mapToSource(index(row, 0))) : QVariantMap();
}
