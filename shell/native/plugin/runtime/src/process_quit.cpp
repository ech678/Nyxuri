#include "process_quit.h"
#include <QSet>
#include <cerrno>
#include <climits>
#include <csignal>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

void ProcessQuit::cancel()
{
    for (int fd : m_handles)
        close(fd);
    m_handles.clear();
}

bool ProcessQuit::prepare(const QVariantList &pids)
{
    cancel();
    QSet<qint64> seen;
    for (const auto &value : pids) {
        bool ok = false;
        const auto pid = value.toLongLong(&ok);
        if (!ok || pid <= 1 || pid > INT_MAX || pid == getpid()) {
            cancel();
            return false;
        }
        if (seen.contains(pid))
            continue;
        seen.insert(pid);
        const int fd = syscall(SYS_pidfd_open, pid, 0);
        if (fd < 0) {
            if (errno == ESRCH)
                continue;
            cancel();
            return false;
        }
        struct stat info{};
        const auto path = QStringLiteral("/proc/%1").arg(pid).toLocal8Bit();
        if (stat(path.constData(), &info) != 0 || info.st_uid != getuid()) {
            close(fd);
            cancel();
            return false;
        }
        m_handles.push_back(fd);
    }
    return !m_handles.empty();
}

bool ProcessQuit::confirm()
{
    bool ok = !m_handles.empty();
    for (int fd : m_handles) {
        // ESRCH means the process exited while the confirmation was open.
        if (syscall(SYS_pidfd_send_signal, fd, SIGKILL, nullptr, 0) != 0 && errno != ESRCH)
            ok = false;
    }
    cancel();
    return ok;
}
