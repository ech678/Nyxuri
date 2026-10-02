#include "clavis_build_info.h"

#include "clavis_release.h"

ClavisBuildInfo::ClavisBuildInfo(QObject *parent) : QObject(parent) {}

QString ClavisBuildInfo::release() const { return QStringLiteral(CLAVIS_RELEASE); }

QString ClavisBuildInfo::commit() const { return QStringLiteral(CLAVIS_COMMIT); }

QString ClavisBuildInfo::buildTime() const { return QStringLiteral(CLAVIS_BUILD_TIME); }
