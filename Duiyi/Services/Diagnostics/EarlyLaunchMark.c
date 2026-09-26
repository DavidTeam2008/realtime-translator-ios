// EarlyLaunchMark.c
//
// 目的：让 **pre-main（dyld + 镜像初始化）** 的耗时可见。
//
// 背景：AppLaunchTracker 是 Swift 单例，第一次被触碰是在 DuiyiApp.init() 里 ——
// 而 Swift 属性初始化器（@State var coordinator = AppCoordinator()）先于 init() 执行。
// 于是「进程创建 → 埋点首次触碰」这段（实测约 219ms，占启动 54%）完全没被归因。
//
// 本文件的构造函数由 dyld 在**任何 Swift 代码之前**执行，因此它记录的
// 「进程创建 → 本镜像构造函数」就是 pre-main 耗时。
//
// 刻意用纯 C + os_log 输出，不引入 Swift/C 互操作（否则要配 bridging header，改动工程配置）。
// 输出到与 AppLaunchTracker 相同的 subsystem，日志可按时间先后拼接。

#include <os/log.h>
#include <sys/sysctl.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>

__attribute__((constructor))
static void duiyi_early_launch_mark(void) {
    // 进程创建时间（与 AppLaunchTracker.processStartTime 同一口径）
    int mib[4] = {CTL_KERN, KERN_PROC, KERN_PROC_PID, getpid()};
    struct kinfo_proc info;
    size_t size = sizeof(info);
    if (sysctl(mib, 4, &info, &size, NULL, 0) != 0) {
        return;
    }

    struct timeval start_tv = info.kp_proc.p_starttime;
    double start = (double)start_tv.tv_sec + (double)start_tv.tv_usec / 1000000.0;

    struct timeval now_tv;
    gettimeofday(&now_tv, NULL);
    double now = (double)now_tv.tv_sec + (double)now_tv.tv_usec / 1000000.0;

    int premain_ms = (int)((now - start) * 1000.0);
    if (premain_ms < 0) {
        premain_ms = 0;  // 时钟异常时不报负数
    }

    os_log_t log = os_log_create("com.david.Duiyi", "launch");
    os_log(log, "EARLY pre-main: %{public}d ms since process start", premain_ms);
}
